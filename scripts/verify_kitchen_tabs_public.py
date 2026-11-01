"""Verify real public HTTPS kitchen previews; optionally publish synthetic evidence."""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

OUT = Path('/tmp/kitchen-tabs-public')
RESULT_BRANCH = 'preview/kitchen-tabs-validation-20261101'
PROFILES = [('desktop',649,900),('phone',390,844),('small-phone',320,660)]
FIXTURES = Path(__file__).resolve().parent/'fixtures/kitchen-flow-ocr'
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


def close_tray(frame):
    if frame.locator('#tray').evaluate('e=>e.open'):
        frame.locator('#closeTray').click()
    expect(frame.locator('#tray')).not_to_be_visible()


def center(locator):
    locator.evaluate("e=>e.scrollIntoView({block:'center',behavior:'instant'})")


HOME_PAGES = {
    'homeRecommendation': ('meals','recommendation'),
    'homePlans': ('meals','plans'),
    'homeNutrition': ('records','nutrition'),
    'homeBudget': ('records','budget'),
    'homeSupplements': ('records','supplements'),
    'homeMonthly': ('records','monthly'),
    'homeGrowth': ('kitchen','growth'),
    'homeConnections': ('kitchen','connections'),
}


def show_page(frame, block):
    """Select actual painted tabs; never reveal content through script mutation."""
    main, sub = HOME_PAGES[block]
    frame.locator(f'[data-home-tab="{main}"]').click()
    frame.locator(f'[data-home-subtab="{sub}"]').click()
    expect(frame.locator('#'+block)).to_be_visible()
    return frame.locator('#'+block)


def records_hub(frame):
    show_page(frame,'homeNutrition')
    frame.locator('#homeNutrition [data-workflow="hub"]').click()
    expect(frame.locator('#tray')).to_be_visible()


def check_tabs(frame):
    before=frame.evaluate('KitchenJournal.getEnvelope()')
    for block in HOME_PAGES:
        show_page(frame,block)
        expect(frame.locator('.home-panel:not([hidden])')).to_have_count(1)
        expect(frame.locator('.home-panel:not([hidden]) [data-home-page]:not([hidden])')).to_have_count(1)
        expect(frame.locator('[data-home-tab][aria-selected="true"]')).to_have_count(1)
        assert frame.evaluate('document.documentElement.scrollHeight<=innerHeight+1 && scrollY===0'), block
        assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth'), block
        for tab in frame.locator('[data-home-tab]').all():
            r=tab.bounding_box();assert r and r['height']>=44 and r['width']>=44, r
    frame.locator('[data-home-tab="fridge"]').click()
    expect(frame.locator('#kitchen')).to_be_visible()
    assert frame.evaluate('KitchenJournal.getEnvelope()')==before, 'Tab browsing must not write any data'
    return {'main_tabs':4,'active_home_page_count':1,'all_eight_subpages_reachable':True,
        'no_document_scrolling_or_horizontal_overflow':True,'navigation_writes_no_records':True}


def check_home(page, frame, touch):
    """Use actual forms to prove the overview changes with records, not just cards."""
    day=frame.evaluate("(()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')})()")
    world=frame.evaluate('MiniKitchen.exportWorld()')
    for block in ['homeRecommendation','homePlans','homeBudget','homeSupplements','homeMonthly','homeGrowth','homeConnections']:
        locator=show_page(frame,block);expect(locator).to_be_visible()
        assert locator.inner_text().strip(), 'Empty home section '+block
    show_page(frame,'homeRecommendation')
    recommendation=frame.locator('#homeRecommendation [data-home-recipe]')
    assert recommendation.count()==1
    expected=frame.evaluate('KitchenHome.recommendation()?.recipe.id||""')
    assert recommendation.get_attribute('data-home-recipe')==expected
    assert frame.locator('[data-recommended-recipe]').get_attribute('data-recommended-recipe')==expected
    expect(frame.locator('#homeRecommendation [data-home-cost]')).to_contain_text('미입력')
    expect(frame.locator('#homeRecommendation [data-home-kcal]')).to_contain_text('미입력')

    show_page(frame,'homeBudget')
    budget_link=frame.locator('#homeBudget [data-workflow="budget"]');center(budget_link);budget_link.click()
    budget=frame.locator('[data-wf-form="budget"]');expect(budget).to_be_visible()
    budget.locator('[name="budget"]').fill('120000');budget.locator('[type="submit"]').click()
    expense=frame.locator('[data-wf-form="expense"]');center(expense)
    expense.locator('[name="day"]').fill(day);expense.locator('[name="name"]').fill('공개 검사 장보기')
    expense.locator('[name="amount"]').fill('5000');expense.locator('[type="submit"]').click();close_tray(frame)
    assert frame.evaluate('KitchenJournal.getWorkflow().budgets')[day[:7]]==120000
    expect(frame.locator('#homeBudget [data-home-budget]')).to_contain_text('115,000')
    show_page(frame,'homeMonthly')
    expect(frame.locator('#homeMonthly')).to_contain_text('5,000')

    show_page(frame,'homeSupplements')
    supplement_link=frame.locator('#homeSupplements [data-workflow="supplements"]');center(supplement_link);supplement_link.click()
    form=frame.locator('[data-wf-form="supplement"]');center(form)
    form.locator('[name="name"]').fill('검사 영양제');form.locator('[name="amount"]').fill('제품 표시량 확인')
    form.locator('[name="schedule"]').fill('아침 식후');form.locator('[type="submit"]').click();close_tray(frame)
    check=frame.locator('#homeSupplements [data-home-supplement]');assert check.count()==1;center(check)
    (check.tap if touch else check.click)()
    frame.wait_for_function('day=>KitchenJournal.getWorkflow().supplements.some(s=>s.name==="검사 영양제"&&s.days.includes(day))',arg=day)
    expect(frame.locator('#homeSupplements')).to_contain_text('오늘 체크 1/1')

    show_page(frame,'homePlans')
    plan_link=frame.locator('#homePlans [data-workflow="plan"]');center(plan_link);plan_link.click()
    plan=frame.locator('[data-wf-form="plan"]');center(plan)
    plan.locator('[name="day"]').fill(day);plan.locator('[name="recipeId"]').select_option('recipe-1')
    plan.locator('[name="portions"]').fill('3');plan.locator('[type="submit"]').click()
    log=frame.locator('#tray .plan-row [data-wf="logPlan"]');assert log.count()==1;log.click()
    meal=frame.locator('#workflowMealForm');expect(meal).to_be_visible()
    expect(meal.locator('[name="portions"]')).to_have_value('3');expect(meal.locator('[name="day"]')).to_have_value(day)
    close_tray(frame)
    expect(frame.locator('#homePlans')).to_contain_text('3회분')
    shopping=frame.locator('#homePlans [data-wf="planShopping"]');center(shopping);shopping.click()
    actual={r['name']:r['quantity'] for r in frame.evaluate('KitchenJournal.getWorkflow().shopping')}
    assert actual.get('양파') in ('0.75개','3/4개'), actual
    assert actual.get('식용유')=='3작은술', actual
    assert actual.get('밥/즉석밥')=='3공기', actual
    close_tray(frame)

    show_page(frame,'homeMonthly')
    monthly=frame.locator('#homeMonthly [data-workflow="monthly"]');center(monthly);monthly.click()
    expect(frame.locator('#reviewMonth')).to_have_value(day[:7]);close_tray(frame)
    show_page(frame,'homeGrowth')
    book=frame.locator('#homeGrowth [data-workflow="book"]').first;center(book);book.click()
    expect(frame.locator('#journalGoal')).to_be_visible()
    frame.locator('#journalGoal').select_option('recording');close_tray(frame)
    assert frame.evaluate('KitchenJournal.getSnapshot().goal')=='recording'
    expect(frame.locator('#homeGrowth')).to_contain_text('오늘 식사 한 끼 기록하기')
    reward=frame.locator('#homeGrowth [data-workflow="rewards"]');center(reward);reward.click()
    expect(frame.locator('.reward-catalog')).to_be_visible();close_tray(frame)
    show_page(frame,'homeConnections')
    details=frame.locator('#homeConnections details.home-data-status');center(details)
    if not details.evaluate('e=>e.open'):details.locator('summary').click()
    expect(details).to_contain_text('임시 세션');expect(details).to_contain_text('권장량은 연결 전')
    assert frame.evaluate('MiniKitchen.exportWorld()')==world, 'Overview form/navigation checks must not consume stock'
    frame.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    frame.locator('[data-home-tab="fridge"]').click()
    page.screenshot(path=str(OUT/('home-'+frame.locator('body').get_attribute('data-mode')+'-'+str(frame.evaluate('innerWidth'))+'.png')),full_page=True)
    return {'recommendation_and_lcd_match':True,'unknown_nutrition_and_cost_remain_unknown':True,
        'budget_after_real_120000_budget_5000_expense':115000,'supplement_actual_check':True,
        'planned_portions_carried_to_meal_form':3,'plan_shopping':actual,
        'monthly_goal_reward_and_connections_reachable':True,'no_unconfirmed_stock_writes':True}


def fixture_data(name):
    path=FIXTURES/name
    data=path.read_bytes()
    assert data.startswith(b'\x89PNG\r\n\x1a\n'), 'Expected synthetic PNG fixture: '+str(path)
    return 'data:image/png;base64,'+base64.b64encode(data).decode('ascii')


def check_photo_gate(frame):
    """UI admits OCR only with both original files and keeps manual fallback."""
    before=frame.evaluate('MiniKitchen.exportWorld()')
    expect(frame.locator('[data-photo]')).to_have_count(2)
    gate=frame.locator('[data-wf="readPhotos"]');expect(gate).to_be_disabled()
    frame.locator('[data-photo="product"]').set_input_files(FIXTURES/'product.png')
    expect(gate).to_be_disabled()
    frame.locator('[data-photo="expiry"]').set_input_files(FIXTURES/'expiry.png')
    expect(gate).to_be_enabled()
    expect(frame.locator('[data-wf="manualAdd"]')).to_be_enabled()
    assert frame.evaluate('MiniKitchen.exportWorld()')==before, 'Selecting photos must not write inventory'


def check_actual_ocr(page, frame, touch, requests, responses):
    """No proxy/routing/stub: run the committed engine against synthetic labels."""
    before=frame.evaluate('MiniKitchen.exportWorld()');start=len(requests);response_start=len(responses)
    values={'product':fixture_data('product.png'),'expiry':fixture_data('expiry.png')}
    result=frame.evaluate('async values=>await KitchenPhotoReader.read(values)',values)
    assert any(''.join(s.split())=='신선한우유' for s in result['nameCandidates']), result
    assert '500mL' in result['quantityCandidates'], result
    assert '2026-11-30' in result['expiryCandidates'], result
    assert result['text']['product'].strip() and result['text']['expiry'].strip(), result
    assert frame.evaluate('MiniKitchen.exportWorld()')==before, 'OCR candidates must not auto-save inventory'

    # Also exercise the actual two-file UI pipeline after the direct API check.
    gate=frame.locator('[data-wf="readPhotos"]');center(gate)
    (gate.tap if touch else gate.click)()
    review=frame.locator('form[data-wf-form="photoReview"]');expect(review).to_be_visible(timeout=150000)
    expect(review.locator('[name="confirmed"]')).not_to_be_checked()
    assert frame.evaluate('MiniKitchen.exportWorld()')==before, 'Unconfirmed UI review must not save stock'
    expect(review.locator('[name="expiry"]')).to_have_value('2026-11-30')
    assert '우유' in review.locator('[name="name"]').input_value()
    review.locator('[name="confirmed"]').check();review.locator('[type="submit"]').click()
    final=frame.locator('[data-wf-form="add"]');expect(final).to_be_visible()
    expect(final.locator('[name="expiry"]')).to_have_value('2026-11-30')
    assert frame.evaluate('MiniKitchen.exportWorld()')==before, 'Review confirmation opens final form; only final save may write'

    sent=[r for r in requests[start:] if r['url'].startswith(('http://','https://'))]
    assert all(r['method'] in ('GET','HEAD','OPTIONS') and r['body_bytes']==0 for r in sent), sent
    assert all(urlparse(r['url']).hostname in ('cdn.jsdelivr.net','raw.githubusercontent.com') for r in sent), sent
    observed=[r for r in responses[response_start:] if r['url'].startswith(('https://cdn.jsdelivr.net/','https://raw.githubusercontent.com/tesseract-ocr/'))]
    assert any('tesseract.min.js' in r['url'] and r['status']==200 for r in observed), observed
    assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.screenshot(path=str(OUT/('ocr-'+frame.locator('body').get_attribute('data-mode')+'-review.png')),full_page=True)
    return {'executed':True,'expected_name_found':True,'expected_500mL_found':True,'expected_2026_11_30_found':True,
        'confidence':result.get('confidence'),'text':result['text'],'warnings':result['warnings'],
        'actual_ui_review_confirmed_before_final_add_form':True,'no_inventory_write_before_final_save':True,
        'no_remote_photo_post_or_sync':True,'external_requests':sent,'dependency_responses':observed}


def publish_results():
    parent = git('ls-remote','--heads','origin','refs/heads/'+RESULT_BRANCH).split()
    if parent:
        git('fetch','origin','refs/heads/'+RESULT_BRANCH)
    with tempfile.TemporaryDirectory(prefix='kitchen-flow-result-') as folder:
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
        commit=git(*args,'-m','Record kitchen flow public HTTPS browser verification')
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
        'cases':[],'scope':'Actual public HTTPS HTMLPreview execution in six fresh Chromium desktop/touch profiles; pinned raw source hashes; real on-device Korean/date OCR in app-phone and widget-phone through the original public CDN URLs. No network routing, mocks, TLS relaxation, physical-device, Safari, Notion or persistent-preview-storage claim.'}
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
                    page=ctx.new_page();errors=[];sources=[];requests=[];responses=[]
                    ctx.on('request',lambda r,bucket=requests:bucket.append({'url':r.url,'method':r.method,'resource_type':r.resource_type,'body_bytes':len(r.post_data_buffer or b'')}))
                    ctx.on('response',lambda r,bucket=responses:bucket.append({'url':r.url,'status':r.status}))
                    page.on('pageerror',lambda e,bucket=errors:bucket.append(str(e)))
                    page.on('response',lambda r,bucket=sources,expected=raw:bucket.append(r) if r.url==expected else None)
                    try:
                        response=page.goto(url,wait_until='domcontentloaded',timeout=45000)
                        case['http_status']=response.status
                        assert response.status==200
                        wrapper=page.locator('iframe[sandbox="allow-scripts allow-forms"]')
                        expect(wrapper).to_be_attached(timeout=45000)
                        frame=wrapper.element_handle().content_frame()
                        frame.wait_for_function('window.MiniKitchen && window.KitchenJournal && window.KitchenWorkflows && window.KitchenHome && window.KitchenPhotoReader',timeout=30000)
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
                        case['tab_navigation']=check_tabs(frame)
                        case['live_home_overview']=check_home(page,frame,touch)
                        page.screenshot(path=str(OUT/(label+'-initial.png')),full_page=True)
                        check_independent_doors(page,frame,touch)
                        case['four_independent_real_door_gestures']=True
                        check_first_frame(page,frame,touch)
                        case['opening_first_frame_occludes_food']=True
                        condiment=frame.locator('[data-item="spice0"]')
                        expect(condiment.locator('.sauce-label')).to_have_count(1)
                        expect(condiment.locator('.item-name,.quantity')).to_have_count(0)
                        case['one_subtle_sauce_label_no_duplicate_badges']=True
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
                        records_hub(frame)
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
                        frame.locator('[data-home-tab="fridge"]').click()
                        frame.locator('#addFood').click()
                        frame.locator('[data-wf="photos"]').click()
                        assert frame.locator('[data-photo]').count()==2
                        check_photo_gate(frame)
                        case['photo_two_originals_gate_and_manual_fallback']=True
                        if profile=='phone':
                            case['on_device_ocr']=check_actual_ocr(page,frame,touch,requests,responses)
                        else:
                            case['on_device_ocr']={'executed':False,'reason':'Actual engine is exercised on both app-phone and widget-phone profiles; this profile verifies the input gate only'}
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
