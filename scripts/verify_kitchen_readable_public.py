"""Verify real public HTTPS kitchen previews; optionally publish synthetic evidence."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

OUT = Path('/tmp/kitchen-readable-public')
RESULT_BRANCH = 'preview/kitchen-readable-validation-20261101'
PROFILES = [('desktop',649,900),('phone',390,844),('small-phone',320,660)]
DOORS = ('freshLeft','freshRight','frozenLeft','frozenRight')
HUB_ROUTES = ('nutrition','plan','supplements','shopping','budget','monthly','book','decor','inventory','settings')


def git(*args, env=None):
    return subprocess.run(['git',*args],env=env,check=True,capture_output=True,text=True).stdout.strip()


def tap_door(page, frame, key, touch):
    """Tap a genuinely reachable painted surface, rather than calling e.click()."""
    door = frame.locator(f'[data-door="{key}"]')
    door.scroll_into_view_if_needed()
    point = door.evaluate('''e=>{
        const r=e.getBoundingClientRect();
        for(const fy of [.12,.2,.8,.9,.5])for(const fx of [.12,.2,.8,.9,.5]){
            const x=r.x+r.width*fx,y=r.y+r.height*fy;
            if(x<1||y<1||x>=innerWidth-1||y>=innerHeight-1)continue;
            if(document.elementFromPoint(x,y)?.closest('[data-door]')===e)return {x,y};
        }
        return null;
    }''')
    assert point, 'No reachable visible surface on '+key
    offset = frame.frame_element().bounding_box()
    assert offset, 'Public iframe has no visible bounding box'
    x,y = point['x']+offset['x'], point['y']+offset['y']
    (page.touchscreen.tap if touch else page.mouse.click)(x,y)


def check_independent_doors(page, frame, touch):
    before = frame.evaluate('MiniKitchen.getSnapshot().doors')
    assert set(before)==set(DOORS) and all(before.values()), before
    for key in DOORS:
        expected = dict(before)
        expected[key] = False
        tap_door(page,frame,key,touch)
        frame.wait_for_function('expected=>{const actual=MiniKitchen.getSnapshot().doors;return Object.keys(actual).length===4&&Object.entries(expected).every(([k,v])=>actual[k]===v)}',arg=expected)
        if key in ('freshLeft','freshRight'):
            expect(frame.locator(f'[data-lcd="{key}"]')).to_be_visible()
            expect(frame.locator(f'[data-lcd="{key}"] .lcd-title')).to_have_text('유통기한 임박' if key=='freshLeft' else '오늘의 추천메뉴')
        tap_door(page,frame,key,touch)
        frame.wait_for_function('expected=>{const actual=MiniKitchen.getSnapshot().doors;return Object.keys(actual).length===4&&Object.entries(expected).every(([k,v])=>actual[k]===v)}',arg=before)


def check_first_frame(page, frame, touch):
    """Real close/open tests above are separate from this paused compositor probe."""
    page.emulate_media(reduced_motion='no-preference')
    tap_door(page,frame,'freshLeft',touch)
    frame.wait_for_function('!MiniKitchen.getSnapshot().doors.freshLeft && !MiniKitchen.isDoorClosing("freshLeft")')
    frame.wait_for_function('[...document.querySelectorAll("[data-door=\\"freshLeft\\"]")].every(e=>e.getAnimations().every(a=>a.playState==="finished"))')
    frame.locator('[data-door="freshLeft"]').evaluate('''e=>{
        e.click();const a=e.getAnimations().find(a=>a.transitionProperty==='transform');
        if(!a)throw new Error('Expected a real opening transition');a.pause();a.currentTime=0;
    }''')
    sample = frame.evaluate('''()=>{
        const r=document.querySelector('[data-item="egg"]').getBoundingClientRect();
        const e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
        return {door:e?.closest('[data-door]')?.dataset.door||null,item:e?.closest('[data-item]')?.dataset.item||null};
    }''')
    assert sample=={'door':'freshLeft','item':None}, sample
    frame.locator('[data-door="freshLeft"]').evaluate('e=>e.getAnimations().forEach(a=>a.finish())')
    page.emulate_media(reduced_motion='reduce')


def check_dock(frame):
    measurements = frame.evaluate('''()=>{
        window.scrollTo({top:0,behavior:'instant'});
        return ['addFood','recipes','openRecords'].map(id=>{
            const e=document.getElementById(id),r=e.getBoundingClientRect();
            const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
            return {id,x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right,
                reachable:hit?.closest('button')===e,viewport:[innerWidth,innerHeight]};
        });
    }''')
    for r in measurements:
        assert r['width']>=44 and r['height']>=44, r
        assert r['x']>=0 and r['y']>=0 and r['right']<=r['viewport'][0]+1 and r['bottom']<=r['viewport'][1]+1, r
        assert r['reachable'], r
    return measurements


def publish_results():
    parent = git('ls-remote','--heads','origin','refs/heads/'+RESULT_BRANCH).split()
    if parent:
        git('fetch','origin','refs/heads/'+RESULT_BRANCH)
    with tempfile.TemporaryDirectory(prefix='kitchen-readable-result-') as folder:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
        git('read-tree',parent[0] if parent else '--empty',env=env)
        for path in OUT.iterdir():
            if path.is_file() and path.suffix in ('.png','.json'):
                blob=git('hash-object','-w',str(path))
                git('update-index','--add','--cacheinfo','100644,'+blob+','+path.name,env=env)
        tree=git('write-tree',env=env)
        args=['-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',tree]
        if parent:
            args+=['-p',parent[0]]
        commit=git(*args,'-m','Record readable kitchen public HTTPS browser verification')
        git('push','origin',commit+':refs/heads/'+RESULT_BRANCH)
        return commit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,help='Exact 40-character source commit containing built mobile previews')
    parser.add_argument('--publish-results',action='store_true',help='Publish only validation JSON/PNG to the dedicated result branch')
    args=parser.parse_args()
    source=args.source
    if len(source)!=40 or any(c not in '0123456789abcdef' for c in source):
        raise SystemExit('Use an exact lowercase 40-character commit')
    OUT.mkdir(parents=True,exist_ok=True)
    run_id=os.environ.get('GITHUB_RUN_ID')
    repo=os.environ.get('GITHUB_REPOSITORY','Ohoredingdong/Notion')
    result={'source':source,'run_url':f'https://github.com/{repo}/actions/runs/{run_id}' if run_id else None,
        'cases':[],'scope':'Actual public HTTPS HTMLPreview execution in fresh Chromium desktop and touch/mobile profiles. Raw source bytes are checked against the pinned Git commit. No local proxy, stub, physical-device, Safari or Notion claim.'}
    try:
        with sync_playwright() as p:
            chrome=shutil.which('google-chrome') or shutil.which('chromium')
            if not chrome:
                raise RuntimeError('No Chromium browser installed')
            browser=p.chromium.launch(executable_path=chrome,args=['--no-sandbox'])
            for mode in ('app','widget'):
                raw=f'https://raw.githubusercontent.com/Ohoredingdong/Notion/{source}/previews/mobile/{mode}.html'
                url='https://htmlpreview.github.io/?'+raw
                expected_hash=hashlib.sha256(subprocess.run(['git','show',f'{source}:previews/mobile/{mode}.html'],check=True,capture_output=True).stdout).hexdigest()
                for profile,width,height in PROFILES:
                    label=mode+'-'+profile
                    case={'mode':mode,'profile':profile,'viewport':[width,height],'url':url,'passed':False}
                    touch=profile!='desktop'
                    ctx=browser.new_context(viewport={'width':width,'height':height},has_touch=True,is_mobile=touch,device_scale_factor=2,reduced_motion='reduce',timezone_id='Asia/Seoul')
                    page=ctx.new_page();errors=[];sources=[]
                    page.on('pageerror',lambda e,bucket=errors:bucket.append(str(e)))
                    page.on('response',lambda r,bucket=sources,expected=raw:bucket.append(r) if r.url==expected else None)
                    try:
                        response=page.goto(url,wait_until='domcontentloaded',timeout=45000)
                        case['http_status']=response.status
                        assert response.status==200
                        wrapper=page.locator('iframe[sandbox="allow-scripts allow-forms"]')
                        expect(wrapper).to_be_attached(timeout=45000)
                        frame=wrapper.element_handle().content_frame()
                        frame.wait_for_function('window.MiniKitchen && window.KitchenJournal && window.KitchenWorkflows',timeout=30000)
                        assert frame.locator('body').get_attribute('data-mode')==mode
                        assert frame.locator('[data-balance]').count()==3
                        assert frame.locator('.door').count()==4 and all(frame.evaluate('MiniKitchen.getSnapshot().doors').values())
                        assert frame.evaluate('KitchenJournal.status')=='temporary'
                        assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth')
                        assert frame.locator('.door-label').count()==0
                        assert sources,'No actual raw public source response observed'
                        assert sources[0].status==200
                        case['source_sha256']=hashlib.sha256(sources[0].body()).hexdigest()
                        assert case['source_sha256']==expected_hash
                        case['dock']=check_dock(frame)
                        page.screenshot(path=str(OUT/(label+'-initial.png')),full_page=True)
                        check_independent_doors(page,frame,touch)
                        case['four_independent_real_door_gestures']=True
                        check_first_frame(page,frame,touch)
                        case['opening_first_frame_occludes_food']=True
                        condiment=frame.locator('[data-item="spice0"]')
                        (condiment.tap if touch else condiment.click)()
                        form=frame.locator('#ingredientForm')
                        expect(form).to_be_visible()
                        frame.wait_for_timeout(350)
                        expect(form).to_be_visible()
                        assert form.get_attribute('data-id')=='spice0'
                        case['condiment_form_survives_compatibility_click']=True
                        form.locator('[name="quantity"]').fill('175ml')
                        form.locator('[name="expiry"]').fill('2027-03-01')
                        form.locator('[name="opened"]').fill('2026-11-01')
                        (form.locator('[type="submit"]').tap if touch else form.locator('[type="submit"]').click)()
                        frame.wait_for_function('!document.querySelector("#tray").open')
                        frame.wait_for_timeout(350)
                        expect(frame.locator('#tray')).not_to_be_visible()
                        spice=frame.evaluate('MiniKitchen.exportWorld().items.find(i=>i.id==="spice0")')
                        assert (spice['quantity'],spice['expiry'],spice['opened'])==('175ml','2027-03-01','2026-11-01')
                        expect(condiment).to_be_focused()
                        case['condiment_exact_data_committed']=True
                        frame.locator('#dailyBalance').click()
                        expect(frame.locator('#tray .workflow-nav')).to_have_count(1)
                        expect(frame.locator('#tray .journal-tabs')).to_have_count(0)
                        expect(frame.locator('#tray .workflow-nav [aria-current="page"]')).to_have_text('기록')
                        frame.locator('#tray [data-wf="targets"]').click()
                        target_form=frame.locator('[data-wf-form="targets"]')
                        expect(target_form).to_be_visible()
                        assert frame.locator('#journalExport').count()==0
                        assert not frame.locator('details.target-extras').evaluate('e=>e.open')
                        for key,value in [('carb','230'),('protein','70'),('fat','60')]:
                            expect(target_form.locator(f'[name="{key}"]')).to_be_visible()
                            target_form.locator(f'[name="{key}"]').fill(value)
                        target_form.locator('[type="submit"]').click()
                        actual=frame.evaluate('KitchenJournal.getSnapshot().targets')
                        assert (actual['carb'],actual['protein'],actual['fat'])==(230,70,60)
                        case['direct_targets_no_backup_first_and_optional_collapsed']=True
                        frame.locator('#closeTray').click()
                        frame.locator('#openRecords').click()
                        expect(frame.locator('#tray')).to_be_visible()
                        for route in HUB_ROUTES:
                            link=frame.locator(f'#tray .record-group [data-workflow="{route}"]')
                            link.scroll_into_view_if_needed()
                            expect(link).to_be_visible()
                            expect(link).to_be_enabled()
                        case['all_major_hub_functions_reachable']=True
                        frame.locator('#tray .record-group [data-workflow="settings"]').click()
                        expect(frame.locator('[data-wf-form="targets"]')).to_be_visible()
                        assert frame.locator('#tray h3').first.inner_text()=='내가 정하는 하루 목표'
                        assert not frame.locator('details.target-extras').evaluate('e=>e.open')
                        assert not frame.locator('details.backup-tools').evaluate('e=>e.open')
                        expect(frame.locator('#journalExport')).not_to_be_visible()
                        case['settings_goals_first_backup_collapsed']=True
                        frame.locator('#closeTray').click()
                        frame.locator('#addFood').click()
                        frame.locator('[data-wf="photos"]').click()
                        assert frame.locator('[data-photo]').count()==2
                        expect(frame.locator('button:disabled')).to_contain_text('연결 전')
                        case['photo_registration_is_honest']=True
                        assert frame.evaluate('KitchenJournal.status')=='temporary'
                        assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth')
                        assert not errors,errors
                        page.screenshot(path=str(OUT/(label+'-photo.png')))
                        case['runtime_errors']=errors;case['passed']=True
                    except Exception as error:
                        case['error']=str(error);case['trace']=traceback.format_exc();case['runtime_errors']=errors
                        try:
                            page.screenshot(path=str(OUT/(label+'-failure.png')),full_page=True)
                        except Exception:
                            pass
                    finally:
                        result['cases'].append(case);ctx.close()
            browser.close()
    except Exception:
        result['setup_error']=traceback.format_exc()
    finally:
        result['passed']=len(result['cases'])==6 and all(c['passed'] for c in result['cases'])
        (OUT/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
        if args.publish_results:
            print('Published evidence commit '+publish_results(),flush=True)
    if not result['passed']:
        raise SystemExit(1)

if __name__=='__main__':
    main()
