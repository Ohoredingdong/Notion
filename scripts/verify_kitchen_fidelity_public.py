"""Small actual-HTTPS visual verifier for the approved kitchen composition; no OCR run."""
import argparse,copy,hashlib,html,importlib.util,json,os,re,shutil,subprocess,tempfile,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

OUT=Path('/tmp/kitchen-a5-fidelity-public')
RESULT_BRANCH='preview/kitchen-fidelity-validation-20261103'
PROFILES=[('small-phone',320,660),('phone',390,844),('desktop',649,900),('user-screenshot',801,782)]
DOORS=('freshLeft','freshRight','frozenLeft','frozenRight')

def git(*args,env=None):
    return subprocess.run(['git',*args],env=env,check=True,capture_output=True).stdout

def contract(native):
    # Use the release builder's lossless decoder; it owns codec compatibility
    # and validates the declared original UTF-8 byte count and SHA.
    paths=[Path(__file__).with_name('build_miniature_kitchen_preview.py'),Path('/workspace/Notion/scripts/build_miniature_kitchen_preview.py')]
    builder_path=next(path for path in paths if path.is_file())
    spec=importlib.util.spec_from_file_location('kitchen_release_builder',builder_path);builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    original=builder.unpack_document(native.decode('utf-8'));decoded=original.encode('utf-8')
    scripts=re.findall(r'<script(?:\s[^>]*)?>([\s\S]*?)</script>',original)
    styles=re.findall(r'<style(?:\s[^>]*)?>([\s\S]*?)</style>',original)
    avifs=sorted(set(re.findall(r'data:image/avif;base64,[A-Za-z0-9+/=]+',original)))
    assert len(scripts)==11 and len(styles)==13 and len(avifs)==4,(len(scripts),len(styles),len(avifs))
    return {'decoded_sha256':hashlib.sha256(decoded).hexdigest(),'scripts':scripts,'styles':styles,'avifs':avifs}

def touch(page,frame,node,is_touch):
    point=node.evaluate('''e=>{const r=e.getBoundingClientRect();for(const fy of [.5,.2,.8,.1,.9])for(const fx of [.5,.2,.8,.1,.9]){const x=r.x+r.width*fx,y=r.y+r.height*fy;if(x<0||y<0||x>=innerWidth||y>=innerHeight)continue;if(document.elementFromPoint(x,y)?.closest('button')===e)return {x,y};}return null;}''')
    assert point,'No reachable painted button surface: '+str(node.get_attribute('id') or node.get_attribute('data-door'))
    offset=frame.frame_element().bounding_box();assert offset
    (page.touchscreen.tap if is_touch else page.mouse.click)(point['x']+offset['x'],point['y']+offset['y'])

def target(node):
    expect(node).to_be_visible()
    geometry=node.bounding_box();assert geometry and geometry['width']>=44 and geometry['height']>=44,geometry
    return geometry

def no_page_scroll(frame):
    value=frame.evaluate('()=>({x:scrollX,y:scrollY,width:innerWidth,height:innerHeight,docWidth:document.documentElement.scrollWidth,docHeight:document.documentElement.scrollHeight})')
    assert value['x']==value['y']==0 and value['docWidth']<=value['width']+1 and value['docHeight']<=value['height']+1,value
    return value

def screenshot(page,label,suffix):
    page.screenshot(path=str(OUT/(label+'-'+suffix+'.png')))

def visual_case(page,frame,label,is_touch,data):
    images=frame.evaluate('async urls=>Promise.all(urls.map(async src=>{const i=new Image();i.src=src;await i.decode();return {width:i.naturalWidth,height:i.naturalHeight};}))',data['avifs'])
    assert sorted((i['width'],i['height']) for i in images)==[(1024,1536),(1122,1402),(1402,1122),(1536,1024)],images
    frame.evaluate('async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));}')
    before=frame.evaluate('KitchenJournal.getEnvelope()')
    assert frame.evaluate('KitchenJournal.storageKey')=='miniature-kitchen-preview-v1' and before['version']==1
    expect(frame.locator('[data-home-tab="meals"]')).to_have_text('레시피')
    header=frame.evaluate('''()=>{const box=e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};},notice=document.querySelector('#homeStorageNotice'),inventory=document.querySelector('.masthead .header-actions [data-workflow="inventory"]'),brand=document.querySelector('.masthead .brand h1'),range=document.createRange();range.selectNodeContents(inventory);const label=range.getBoundingClientRect(),x=(label.left+label.right)/2,y=(label.top+label.bottom)/2,hit=document.elementFromPoint(x,y);return {noticeVisible:!!notice.getClientRects().length,notice:box(notice),inventory:box(inventory),brand:box(brand),inventoryLabel:{x,y,width:label.width,height:label.height},inventoryLabelPainted:hit?.closest('button')===inventory};}''')
    def overlaps(a,b):return min(a['right'],b['right'])>max(a['left'],b['left'])+1 and min(a['bottom'],b['bottom'])>max(a['top'],b['top'])+1
    if header['noticeVisible']:
        assert not overlaps(header['notice'],header['inventory']),header
        assert not overlaps(header['notice'],header['brand']),header
    assert not overlaps(header['brand'],header['inventory']),header
    assert header['inventoryLabelPainted'],'Inventory label center is covered: '+str(header)
    add=target(frame.locator('#homeWorktop #addFood'))
    macro=frame.locator('#dailyBalance').evaluate('e=>({height:e.getBoundingClientRect().height,values:[...e.querySelectorAll(".balance-number strong")].map(n=>({text:n.textContent,font:parseFloat(getComputedStyle(n).fontSize)})),names:[...e.querySelectorAll(".balance-name")].map(n=>n.textContent)})')
    assert len(macro['values'])==3 and all(v['font']>=16 for v in macro['values']) and macro['height']>50,macro
    home_frame=frame.locator('.shell').evaluate('e=>{const r=e.getBoundingClientRect(),probe=document.createElement("div");probe.style.cssText="position:fixed;visibility:hidden;pointer-events:none;height:var(--fridge-frame-height);width:1px";document.body.appendChild(probe);const configuredHeight=probe.getBoundingClientRect().height;probe.remove();return {width:r.width,height:r.height,configuredHeight,viewportHeight:innerHeight};}')
    assert abs(home_frame['height']-home_frame['configuredHeight'])<=1 and 0<home_frame['height']<=home_frame['viewportHeight']+1,home_frame
    composition=frame.evaluate('''()=>{const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};return {viewport:[innerWidth,innerHeight],scale:Number(getComputedStyle(document.querySelector('.shell')).getPropertyValue('--home-ui-scale')),stage:box(document.querySelector('.fridge-stage')),stageLogical:{width:document.querySelector('.fridge-stage').offsetWidth,height:document.querySelector('.fridge-stage').offsetHeight},freshDoorFraction:parseFloat(document.querySelector('[data-door="freshLeft"]').style.height)/100,backgroundTop:parseFloat(document.querySelector('.shell').style.getPropertyValue('--bg-image-top')),masthead:box(document.querySelector('.masthead')),balance:box(document.querySelector('#dailyBalance')),nav:box(document.querySelector('.home-shortcuts')),brandFont:parseFloat(getComputedStyle(document.querySelector('.brand h1')).fontSize)};}''')
    assert abs(composition['nav']['height']-48*composition['scale'])<=2,composition
    assert composition['stageLogical']=={'width':711,'height':800} and abs(composition['freshDoorFraction']-.602)<.0001,composition
    assert abs(composition['stage']['width']/composition['stage']['height']-711/800)<.001 and composition['backgroundTop']<0,composition
    if composition['viewport']==[801,782]:
        assert 365<=composition['stage']['width']<=390 and 405<=composition['stage']['height']<=435,composition
        assert 175<=composition['masthead']['height']+composition['balance']['height']<=200 and 82<=composition['nav']['height']<=94 and 23<=composition['brandFont']<=25,composition
    food_art=frame.evaluate('''()=>[...document.querySelectorAll('.room .item.food,.room .item.seasoning')].map(e=>{const art=e.querySelector('.food-art'),r=art.getBoundingClientRect(),css=getComputedStyle(art);let point=null;for(const fy of [.5,.2,.8,.1,.9,.35,.65])for(const fx of [.5,.2,.8,.1,.9,.35,.65]){const x=r.x+r.width*fx,y=r.y+r.height*fy;if(x>=0&&y>=0&&x<innerWidth&&y<innerHeight&&document.elementFromPoint(x,y)?.closest('[data-item]')===e){point={x,y};break;}}return {id:e.dataset.item,name:MiniKitchen.getSnapshot().items.find(i=>i.id===e.dataset.item)?.name,width:r.width,height:r.height,tapPoint:{x:r.x+r.width/2,y:r.y+r.height/2},visible:r.width>0&&r.height>0&&css.display!=='none'&&css.visibility!=='hidden'&&Number(css.opacity)>0,point};})''')
    expected_food={'egg','milk','tofu','broccoli','tomato','fish','scallion','mushroom','kimchi','beef','shrimp','dumplings','mixveg','spice0','spice1','spice2','spice3'}
    assert {row['id'] for row in food_art}==expected_food and all(row['visible'] for row in food_art),food_art
    home_scroll=no_page_scroll(frame);screenshot(page,label,'home')
    # Transparent44px stock hit areas may overlap; actual pointer routing must open
    # the painted food or seasoning under the pointer, never its neighboring empty hit area.
    food_taps=[]
    for food in food_art:
        offset=frame.frame_element().bounding_box();point=food['tapPoint']
        (page.touchscreen.tap if is_touch else page.mouse.click)(point['x']+offset['x'],point['y']+offset['y'])
        detail=frame.locator('#ingredientForm[data-id="'+food['id']+'"]');expect(detail).to_be_visible()
        assert frame.locator('#tray').get_attribute('data-workflow-route')=='item'
        expect(frame.locator('#tray .registration-methods')).not_to_be_visible()
        food_taps.append({'expectedId':food['id'],'actualId':detail.get_attribute('data-id'),'name':food['name'],'artCenterTap':point})
        touch(page,frame,frame.locator('#closeTray'),is_touch)
        assert frame.evaluate('KitchenJournal.getEnvelope()')==before,'Food-art tap must not change stock: '+food['id']


    touch(page,frame,frame.locator('[data-home-tab="meals"]'),is_touch)
    expect(frame.locator('#homeRecommendation')).to_be_visible()
    recipe_frame=frame.locator('.shell').evaluate('e=>{const r=e.getBoundingClientRect();return {width:r.width,height:r.height};}')
    assert abs(recipe_frame['width']-home_frame['width'])<=1,(home_frame,recipe_frame)
    photos=frame.locator('#homeRecommendation .recipe-photo');expect(photos).to_have_count(3)
    photo_fits=photos.evaluate_all('nodes=>nodes.map(n=>n.getAttribute("preserveAspectRatio"))')
    assert all(value=='xMidYMid slice' for value in photo_fits),photo_fits
    assert all(value in data['avifs'] for value in photos.locator('image').evaluate_all('nodes=>nodes.map(n=>n.getAttribute("href"))'))
    cards=frame.locator('#homeRecommendation .home-small-recipe');expect(cards).to_have_count(2)
    card_visibility=cards.evaluate_all('nodes=>nodes.map(e=>{const r=e.getBoundingClientRect(),p=document.querySelector("#todayKitchen").getBoundingClientRect(),nav=document.querySelector(".home-shortcuts").getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height,availableTop:p.top,availableBottom:Math.min(p.bottom,nav.top),fullyVisible:r.top>=p.top-1&&r.bottom<=Math.min(p.bottom,nav.top)+1};})')
    # When all recipe content fits the native component, both secondary cards must be in view.
    fits=frame.locator('#todayKitchen').evaluate('e=>e.scrollHeight<=e.clientHeight+1')
    if fits:assert all(row['fullyVisible'] for row in card_visibility),card_visibility
    no_page_scroll(frame);screenshot(page,label,'recipes')
    recipe=frame.locator('#homeRecommendation .home-featured-recipe [data-wf="recipe"]').first;recipe_id=recipe.get_attribute('data-arg');touch(page,frame,recipe,is_touch)
    discovered=frame.evaluate('KitchenJournal.getEnvelope()');expected=copy.deepcopy(before)
    if recipe_id not in expected['play']['discovered']:expected['play']['discovered'].append(recipe_id)
    assert discovered==expected,'Opening a recipe may only retain its existing discovered-ID behavior'
    before=discovered
    expect(frame.locator('#tray [data-wf="planRecipe"]')).to_be_visible()
    plan=frame.locator('#tray [data-wf="planRecipe"]');target(plan);touch(page,frame,plan,is_touch)
    expect(frame.locator('#tray [data-wf-form="plan"]')).to_be_visible()
    plan_frame=frame.locator('#tray').evaluate('e=>{const r=e.getBoundingClientRect();return {width:r.width,height:r.height};}')
    assert abs(plan_frame['width']-home_frame['width'])<=1,(home_frame,plan_frame)
    assert abs(plan_frame['height']-recipe_frame['height'])<=1,(recipe_frame,plan_frame)
    assert frame.evaluate('KitchenJournal.getEnvelope()')==before
    touch(page,frame,frame.locator('#closeTray'),is_touch);expect(frame.locator('#tray')).not_to_be_visible()

    touch(page,frame,frame.locator('[data-home-tab="kitchen"]'),is_touch)
    expect(frame.locator('#homeGrowth')).to_be_visible()
    expect(frame.locator('#panel-kitchen>.panel-tabs')).not_to_be_visible()
    gear=frame.locator('#panel-kitchen>.hub-heading [data-home-open="connections"]');target(gear);touch(page,frame,gear,is_touch)
    expect(frame.locator('#homeConnections')).to_be_visible()
    touch(page,frame,frame.locator('#panel-kitchen [data-home-subtab="growth"]'),is_touch)
    touch(page,frame,frame.locator('#homeGrowth .home-actions [data-home-open="decor"]'),is_touch)
    expect(frame.locator('#homeDecor')).to_be_visible()
    buttons=frame.locator('.decor-actions button,.decor-selection-toolbar button,.decor-footer button')
    toolbar=[target(buttons.nth(i)) for i in range(buttons.count())]
    prop=frame.locator('#decorStage [data-item="flowers"]');touch(page,frame,prop,is_touch)
    for tool in ('back','front','remove'):expect(frame.locator(f'[data-decor-tool="{tool}"]')).to_be_enabled()
    no_page_scroll(frame);screenshot(page,label,'decor')
    touch(page,frame,frame.locator('[data-decor-tool="back"]'),is_touch)
    touch(page,frame,frame.locator('[data-decor-tool="front"]'),is_touch)
    touch(page,frame,frame.locator('[data-decor-tool="remove"]'),is_touch)
    assert frame.evaluate('KitchenJournal.getEnvelope()')==before,'Decor controls must remain private until Apply'
    touch(page,frame,frame.locator('.decor-footer [data-decor-cancel]'),is_touch)
    assert frame.evaluate('KitchenJournal.getEnvelope()')==before,'Actual Cancel must retain committed data'
    touch(page,frame,frame.locator('[data-home-tab="fridge"]'),is_touch)
    for key in DOORS:
        prior=frame.evaluate('MiniKitchen.getSnapshot().doors');assert prior[key]
        touch(page,frame,frame.locator(f'[data-door="{key}"]'),is_touch)
        after=frame.evaluate('MiniKitchen.getSnapshot().doors');assert after=={**prior,key:False},after
        touch(page,frame,frame.locator(f'[data-door="{key}"]'),is_touch)
        assert frame.evaluate('MiniKitchen.getSnapshot().doors')==prior
    quiet_door=frame.locator('#liveMessage').evaluate('e=>{const r=e.getBoundingClientRect(),c=getComputedStyle(e);return {text:e.textContent,visual:e.dataset.visual,role:e.getAttribute("role"),live:e.getAttribute("aria-live"),width:r.width,height:r.height,clip:c.clipPath,overflow:c.overflow};}')
    assert quiet_door['visual']=='false' and quiet_door['text'] and quiet_door['role']=='status' and quiet_door['live']=='polite' and quiet_door['width']<=1.1 and quiet_door['height']>0 and '50%' in quiet_door['clip'] and quiet_door['overflow']=='hidden',quiet_door
    # Pause a real opening transition at its first painted frame and hit-test the food center.
    touch(page,frame,frame.locator('[data-door="freshLeft"]'),is_touch)
    page.emulate_media(reduced_motion='no-preference')
    touch(page,frame,frame.locator('[data-door="freshLeft"]'),is_touch)
    paused=frame.evaluate('''()=>{const d=document.querySelector('[data-door="freshLeft"]'),a=d.getAnimations().find(a=>a.transitionProperty==='transform');if(!a)return false;a.pause();a.currentTime=0;return true;}''')
    assert paused,'Real door opening transition was not found'
    hit=frame.locator('[data-item="egg"]').evaluate('e=>{const r=e.getBoundingClientRect(),n=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {door:n?.closest("[data-door]")?.dataset.door,item:n?.closest("[data-item]")?.dataset.item};}')
    assert hit.get('door')=='freshLeft' and not hit.get('item'),hit
    frame.evaluate('document.querySelector(\'[data-door="freshLeft"]\').getAnimations().forEach(a=>a.finish())');page.emulate_media(reduced_motion='reduce')
    assert frame.evaluate('KitchenJournal.getEnvelope()')==before

    touch(page,frame,frame.locator('[data-item="milk"]'),is_touch)
    detail=frame.locator('#ingredientForm');expect(detail).to_be_visible()
    fonts=detail.locator('input:not([type="file"]),select').evaluate_all('nodes=>nodes.map(n=>parseFloat(getComputedStyle(n).fontSize))')
    assert fonts and min(fonts)>=16,fonts
    touch(page,frame,frame.locator('#closeTray'),is_touch);expect(frame.locator('#tray')).not_to_be_visible()
    assert frame.evaluate('KitchenJournal.getEnvelope()')==before

    # Explicit isolated example, after all original no-write checks above.
    # The opaque frame is a temporary browser context, never a personal account.
    inventory_before=frame.evaluate('MiniKitchen.exportWorld().items')
    fixture=frame.evaluate('''()=>{const d=new Date(),day=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');KitchenJournal.transact(({play})=>play.record({day,name:'공개 화면 확인용 예시 식사',portion:'1회분',recipeId:'recipe-1',nutrients:{kcal:455,carb:60,protein:20,fat:15,fiber:null,water:null}}));KitchenHome.showTab('fridge');return {day,recipeId:'recipe-1',name:'공개 화면 확인용 예시 식사',scope:'synthetic browser-only view fixture'};}''')
    assert frame.evaluate('MiniKitchen.exportWorld().items')==inventory_before,'Example view fixture must not change actual inventory'
    assert all(frame.evaluate('MiniKitchen.getSnapshot().doors').values())
    expect(frame.locator('#homeWorktop #addFood')).to_be_visible()
    recorded_add=target(frame.locator('#homeWorktop #addFood'))
    screenshot(page,label,'recorded-open-home')
    touch(page,frame,frame.locator('#homeWorktop #addFood'),is_touch)
    expect(frame.locator('#tray .registration-methods')).to_be_visible()
    touch(page,frame,frame.locator('#closeTray'),is_touch)
    for key in DOORS:touch(page,frame,frame.locator(f'[data-door="{key}"]'),is_touch)
    assert not any(frame.evaluate('MiniKitchen.getSnapshot().doors').values())
    expect(frame.locator('#homeFridgeProgress')).to_be_visible()
    expect(frame.locator('#homeWorktop #addFood')).not_to_be_visible()
    progress=frame.locator('#homeFridgeProgress').bounding_box();assert progress and progress['height']>0
    no_page_scroll(frame);screenshot(page,label,'recorded-closed-progress')

    return {'main_composition':composition,'default_seventeen_stock_art':food_art,'default_thirteen_food_art':[row for row in food_art if not row['id'].startswith('spice')],'all_seventeen_actual_stock_art_center_taps':food_taps,'all_thirteen_actual_art_center_taps':[row for row in food_taps if not row['expectedId'].startswith('spice')],'frozen_vegetables_open_correct_detail_not_add':True,'routine_door_announcement_aria_only':quiet_door,'opaque_session_header':header,'shared_frame_sizes':{'home':home_frame,'recipes':recipe_frame,'plan':plan_frame},'recipe_photo_fit':photo_fits,'synthetic_recorded_open_add_target':recorded_add,'synthetic_recorded_closed_progress':progress,'synthetic_fixture':fixture,'inline_avif_decoded_dimensions':images,'home_add_target':add,'macro_native':macro,'home_no_page_scroll':home_scroll,'four_actual_door_buttons':True,'opening_first_frame_occludes_food':True,'ingredient_native_input_fonts':fonts,'recipe_actual_photos':3,'secondary_cards':card_visibility,'recipe_component_fits_content':fits,'recipe_detail_then_plan_opens_native_form_without_write':True,'D1_gear_and_D5_actual_controls':True,'D5_targets':toolbar,'recipe_view_only_discovers_actual_recipe_id':True,'plan_and_cancel_and_remaining_navigation_preserve_exact_envelope':True}

def publish_results():
    previous=git('ls-remote','--heads','origin','refs/heads/'+RESULT_BRANCH).decode().split()
    if previous:git('fetch','--no-write-fetch-head','origin','refs/heads/'+RESULT_BRANCH)
    with tempfile.TemporaryDirectory(prefix='kitchen-fidelity-result-') as folder:
        env={**os.environ,'GIT_INDEX_FILE':str(Path(folder)/'index')};git('read-tree','--empty',env=env)
        for path in OUT.iterdir():
            if path.is_file() and path.suffix in ('.png','.json'):
                blob=git('hash-object','-w',str(path)).decode().strip();git('update-index','--add','--cacheinfo','100644,'+blob+','+path.name,env=env)
        tree=git('write-tree',env=env).decode().strip();parents=['-p',previous[0]] if previous else []
        commit=git('-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',tree,*parents,'-m','Record actual HTTPS kitchen fidelity visual proof').decode().strip()
        git('push','origin',commit+':refs/heads/'+RESULT_BRANCH);return commit

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--publish-results',action='store_true');parser.add_argument('--local-root',type=Path);parser.add_argument('--profiles',nargs='+',choices=[row[0] for row in PROFILES]);args=parser.parse_args();profiles=[row for row in PROFILES if not args.profiles or row[0] in args.profiles]
    assert args.local_root or not args.profiles,'Public proof must run all four profiles'
    assert re.fullmatch('[0-9a-f]{40}',args.source)
    OUT.mkdir(parents=True,exist_ok=True);run=os.environ.get('GITHUB_RUN_ID');repo=os.environ.get('GITHUB_REPOSITORY','Ohoredingdong/Notion')
    result={'source':args.source,'verifier_commit':os.environ.get('GITHUB_SHA'),'run_url':f'https://github.com/{repo}/actions/runs/{run}' if run else None,'cases':[],'scope':'Eight actual HTTPS app/widget visual and native-control profiles, including the user supplied 801x782 viewport; original navigation and Cancel checks preserve data. One explicit isolated browser-only synthetic meal per profile then checks open-home Add and closed-home progress. No OCR, real-user write, physical-device, Safari, Notion or persistent-storage claim.'}
    server=None
    try:
        if args.local_root:
            from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
            import functools,threading
            class Quiet(SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(args.local_root)));threading.Thread(target=server.serve_forever,daemon=True).start()
            result['scope']='LOCAL HTTP calibration only; no public HTTPS or OCR proof.';result['candidate_root']=str(args.local_root)
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
            for mode in ('app','widget'):
                native=(args.local_root/f'miniature-kitchen-{mode}.html').read_bytes() if args.local_root else git('show',args.source+f':previews/miniature-kitchen-{mode}.html')
                raw=(args.local_root/'mobile'/f'{mode}.html').read_bytes() if args.local_root else git('show',args.source+f':previews/mobile/{mode}.html')
                payload=re.search(r'<template id="kitchenSource">([\s\S]*?)</template>',raw.decode());assert payload and html.unescape(payload[1]).encode()==native
                data=contract(native)
                raw_url=f'http://127.0.0.1:{server.server_port}/mobile/{mode}.html' if server else f'https://raw.githubusercontent.com/Ohoredingdong/Notion/{args.source}/previews/mobile/{mode}.html'
                url=raw_url if server else 'https://htmlpreview.github.io/?'+raw_url
                for name,width,height in profiles:
                    case={'mode':mode,'profile':name,'viewport':[width,height],'url':url,'passed':False};label=mode+'-'+name
                    ctx=browser.new_context(viewport={'width':width,'height':height},has_touch=name in ('small-phone','phone'),is_mobile=name in ('small-phone','phone'),device_scale_factor=2,reduced_motion='reduce',locale='ko-KR',timezone_id='Asia/Seoul')
                    page=ctx.new_page();errors=[];sources=[];page.on('pageerror',lambda error,b=errors:b.append(str(error)));page.on('response',lambda response,b=sources,target=raw_url:b.append(response) if response.url==target else None)
                    try:
                        response=page.goto(url,wait_until='domcontentloaded',timeout=45000);case['http_status']=response.status;assert response.status==200
                        iframe=page.locator('iframe[sandbox="allow-scripts allow-forms"]');expect(iframe).to_be_attached(timeout=45000);frame=iframe.element_handle().content_frame();frame.wait_for_function('window.KitchenHome&&window.KitchenJournal&&window.MiniKitchen',timeout=30000)
                        assert sources and sources[0].status==200 and sources[0].body()==raw
                        assert iframe.get_attribute('srcdoc').encode()==native
                        assert frame.locator('script:not([src])').evaluate_all('nodes=>nodes.map(n=>n.textContent)')==data['scripts']
                        assert frame.locator('style').evaluate_all('nodes=>nodes.map(n=>n.textContent)')==data['styles']
                        case.update({'raw_sha256':hashlib.sha256(raw).hexdigest(),'native_sha256':hashlib.sha256(native).hexdigest(),'decoded_sha256':data['decoded_sha256'],'actual_11_modules_13_styles_exact':True})
                        case['visual']=visual_case(page,frame,label,name in ('small-phone','phone'),data);assert not errors,errors;case['passed']=True
                    except Exception as error:
                        case.update({'error':str(error),'trace':traceback.format_exc()});screenshot(page,label,'failure')
                    finally:
                        case['runtime_errors']=errors;result['cases'].append(case);print(label,case['passed'],case.get('error',''),flush=True);ctx.close()
            browser.close()
    except Exception:result['setup_error']=traceback.format_exc()
    finally:
        if server:server.shutdown()
        result['passed']=len(result['cases'])==2*len(profiles) and all(case['passed'] for case in result['cases']);(OUT/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'passed':result['passed'],'source':args.source,'run_url':result['run_url'],'setup_error':result.get('setup_error')},ensure_ascii=False),flush=True)
        if args.publish_results:
            assert not args.local_root,'Never publish local calibration as public evidence'
            print('Evidence commit '+publish_results(),flush=True)
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
