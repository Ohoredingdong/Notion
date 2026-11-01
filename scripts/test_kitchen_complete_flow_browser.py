#!/usr/bin/env python3
"""Real UI kitchen journeys against generated local app/widget/mobile previews.

Set-up uses real forms and controls; model APIs are read-only assertions. The
legacy-storage fixture is the sole intentional non-UI setup. OCR recognition,
Safari, physical devices and a real Notion host require separate verification.
"""
import argparse
import functools
import hashlib
import json
import re
import threading
import traceback
from datetime import datetime
from fractions import Fraction
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

DAY = '2026-11-01'
KEY = 'miniature-kitchen-preview-v1'
ORIGINAL_KEYS = ['use-me-first-state-v5', 'use-me-first-v4', 'use-me-first-life-v1',
                 'use-me-first-kitchen-view-v1', 'umf-seasoning-layout-v3']
FACTS = {'kcal': '78', 'carb': '10', 'protein': '5', 'fat': '2', 'cost': '1000'}
STOCK = {'계란': '6개', '양파': '2개', '식용유': '10작은술', '간장': '10작은술', '밥': '10공기'}


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def quantity(value):
    """Independent expected-value parser; never call the implementation under test."""
    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?(?:/\d+)?)\s*(.*?)\s*', value)
    assert match, value
    return Fraction(match[1]), match[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-executable', default='/usr/bin/chromium')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(repo) or output == root:
        raise SystemExit('Keep generated evidence outside checkout and input root')
    inputs = [root/f'miniature-kitchen-{mode}.html' for mode in ('app', 'widget')]
    inputs += [root/'mobile'/f'{mode}.html' for mode in ('app', 'widget')]
    if not all(path.is_file() for path in inputs):
        raise SystemExit('Build both app/widget and real mobile wrappers before this test')
    output.mkdir(parents=True, exist_ok=True)
    hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    report = {'scope': 'Local Chromium real-form journeys, native and opaque touch; no OCR mocks, physical-device, Safari or Notion claim',
              'day': DAY, 'source_sha256': hashes, 'passed': [], 'failures': [], 'profiles': []}
    errors = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'

    def passed(name):
        report['passed'].append(name)
        print('PASS '+name, flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser_executable, args=['--no-sandbox'])

        def new(mode='app', width=390, height=844, opaque=False, init=None):
            context = browser.new_context(viewport={'width': width, 'height': height}, timezone_id='Asia/Seoul',
                                          reduced_motion='reduce', has_touch=opaque, is_mobile=opaque)
            page = context.new_page()
            page.set_default_timeout(10000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.clock.install(time=datetime.fromisoformat(DAY+'T03:00:00+00:00'))
            if init:
                page.add_init_script(init)
            page.goto(origin+(f'/mobile/{mode}.html' if opaque else f'/miniature-kitchen-{mode}.html'))
            frame = page
            if opaque:
                wrapper = page.locator('iframe[sandbox]')
                expect(wrapper).to_be_attached()
                grants = (wrapper.get_attribute('sandbox') or '').split()
                assert {'allow-scripts', 'allow-forms'} <= set(grants), grants
                assert 'allow-same-origin' not in grants, grants
                frame = wrapper.element_handle().content_frame()
            frame.wait_for_function('window.MiniKitchen&&window.KitchenJournal&&window.KitchenWorkflows&&window.KitchenHome&&window.KitchenJourneyModel')
            return context, page, frame

        def envelope(frame):
            return frame.evaluate('KitchenJournal.getEnvelope()')

        def close(frame):
            if frame.locator('#tray').is_visible():
                frame.locator('#closeTray').click()

        def go(frame, route):
            close(frame)
            frame.locator('#openRecords').click()
            frame.locator(f'#tray .record-group [data-workflow="{route}"]').click()
            expect(frame.locator('#tray')).to_be_visible()

        def recipe(frame, recipe_id='recipe-1'):
            close(frame)
            frame.locator('#recipes').click()
            card = frame.locator(f'#tray [data-wf="recipe"][data-arg="{recipe_id}"]')
            if card.count() == 0:
                frame.locator('#tray .recipe-filters summary').click()
                frame.locator('#tray [data-wf="recipesReset"]').click()
            frame.locator(f'#tray [data-wf="recipe"][data-arg="{recipe_id}"]').click()

        def facts(frame, values=FACTS, recipe_id='recipe-1'):
            recipe(frame, recipe_id)
            frame.locator('#tray [data-wf="recipeFacts"]').click()
            form = frame.locator('[data-wf-form="facts"]')
            for name, value in values.items():
                form.locator(f'[name="{name}"]').fill(value)
            form.locator('[name="source"]').fill('브라우저 검사 직접 입력 · 기준 1회분')
            form.locator('[type="submit"]').click()
            saved = envelope(frame)['workflow']['recipeFacts'][recipe_id]
            for name, value in values.items():
                assert saved[name] == (float(value) if value else None), saved

        def stock_ui(frame, amounts=STOCK):
            """Edit/add actual inventory, with known compatible units and printed dates."""
            for name, amount in amounts.items():
                items = [row for row in envelope(frame)['world']['items']
                         if row['name'] == name and row['kind'] in ('food', 'seasoning')]
                if items:
                    for index, item in enumerate(items):
                        go(frame, 'inventory')
                        frame.locator(f'#tray [data-wf="item"][data-arg="{item["id"]}"]').click()
                        form = frame.locator('#ingredientForm')
                        form.locator('[name="quantity"]').fill(amount if index == 0 else '0'+quantity(amount)[1])
                        form.locator('[name="expiry"]').fill('2026-12-01')
                        form.locator('[name="opened"]').fill(DAY)
                        form.locator('[type="submit"]').click()
                else:
                    close(frame)
                    frame.locator('#addFood').click()
                    frame.locator('#tray [data-wf="manualAdd"]').click()
                    form = frame.locator('#addIngredientForm')
                    for key, value in {'name': name, 'quantity': amount, 'expiry': '2026-12-01', 'opened': DAY}.items():
                        form.locator(f'[name="{key}"]').fill(value)
                    form.locator('[name="kind"]').select_option('seasoning' if name in ('식용유', '간장') else 'food')
                    form.locator('[name="zone"]').select_option('doorFreshRight' if name in ('식용유', '간장') else 'freshLeft')
                    form.locator('[type="submit"]').click()
                actual = [row for row in envelope(frame)['world']['items'] if row['name'] == name]
                assert actual[0]['quantity'] == amount and actual[0]['expiry'] == '2026-12-01', actual
            close(frame)

        def plan(frame, portions, day=DAY, slot='lunch'):
            before = {row['id'] for row in envelope(frame)['workflow']['plans']}
            go(frame, 'plan')
            form = frame.locator('[data-wf-form="plan"]')
            form.locator('[name="day"]').fill(day)
            form.locator('[name="slot"]').select_option(slot)
            form.locator('[name="recipeId"]').select_option('recipe-1')
            form.locator('[name="portions"]').fill(str(portions))
            form.locator('[type="submit"]').click()
            added = [row for row in envelope(frame)['workflow']['plans'] if row['id'] not in before]
            assert len(added) == 1 and added[0]['day'] == day and added[0]['portions'] == portions, added
            return added[0]['id']

        def view_plans(frame, day):
            go(frame, 'plan')
            frame.locator('#planDay').fill(day)
            frame.locator('#planDay').dispatch_event('change')

        def usage(frame):
            return frame.locator('#mealUsageRows .usage-row').evaluate_all('''rows=>rows.map(row=>({
                name:row.querySelector('strong').textContent,
                id:row.querySelector('[type=hidden]').value,
                quantity:row.querySelector('[type=text]').value,
                checked:row.querySelector('[type=checkbox]').checked,
                disabled:row.querySelector('[type=checkbox]').disabled
            }))''')

        def scaled_form(frame, plan_id, portions, day):
            form = frame.locator('#workflowMealForm')
            expect(form).to_be_visible()
            assert form.get_attribute('data-plan') == plan_id
            assert form.locator('[name="day"]').input_value() == day
            assert float(form.locator('[name="portions"]').input_value()) == portions
            for name in ('kcal', 'carb', 'protein', 'fat'):
                assert float(form.locator(f'[name="{name}"]').input_value()) == float(FACTS[name])*portions, name
            expected = {'계란': (Fraction(portions), '개'), '양파': (Fraction(portions, 4), '개'),
                        '식용유': (Fraction(portions), '작은술'), '간장': (Fraction(portions), '작은술'),
                        '밥/즉석밥': (Fraction(portions), '공기')}
            actual = {}
            for row in usage(frame):
                assert row['checked'] and not row['disabled'], row
                value, unit = quantity(row['quantity'])
                if row['name'] in actual:
                    assert actual[row['name']][1] == unit
                    value += actual[row['name']][0]
                actual[row['name']] = value, unit
            assert actual == expected, (actual, expected)
            expect(form.locator('#mealCost')).to_contain_text(f'{1000*portions:,}원')
            return form

        def no_overflow(frame):
            assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            if frame.locator('#tray').is_visible():
                assert not frame.locator('#tray').evaluate('e=>e.scrollWidth>e.clientWidth+1')

        def dock(frame):
            rows = frame.evaluate('''()=>['addFood','recipes','openRecords'].map(id=>{
                const e=document.getElementById(id),r=e.getBoundingClientRect();
                return {id,width:r.width,height:r.height,visible:r.top>=0&&r.bottom<=innerHeight+1&&r.left>=0&&r.right<=innerWidth+1,
                    hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===e};})''')
            assert all(row['visible'] and row['hit'] and row['height'] >= 44 for row in rows), rows

        def tap_door(page, frame, key, touch=False):
            locator = frame.locator(f'[data-door="{key}"]')
            locator.scroll_into_view_if_needed()
            point = locator.evaluate('''e=>{const r=e.getBoundingClientRect();
                for(const fy of [.12,.2,.8,.9,.5])for(const fx of [.12,.2,.8,.9,.5]){
                    const x=r.x+r.width*fx,y=r.y+r.height*fy;
                    if(x>0&&y>0&&x<innerWidth&&y<innerHeight&&document.elementFromPoint(x,y)?.closest('[data-door]')===e)return{x,y};
                }return null;}''')
            assert point, 'No reachable '+key
            if frame != page:
                offset = frame.frame_element().bounding_box()
                point = {'x': point['x']+offset['x'], 'y': point['y']+offset['y']}
            (page.touchscreen.tap if touch else page.mouse.click)(point['x'], point['y'])

        try:
            # Six native layouts and the four actual opaque wrappers. Every
            # required home section has a real, reachable entry into its route.
            profiles = [(mode, width, height, False) for mode in ('app', 'widget')
                        for width, height in ((320, 660), (390, 844), (1120, 1000))]
            profiles += [(mode, width, height, True) for mode in ('app', 'widget')
                         for width, height in ((320, 660), (390, 844))]
            for mode, width, height, opaque in profiles:
                context, page, frame = new(mode, width, height, opaque)
                no_overflow(frame)
                dock(frame)
                assert all(envelope(frame)['world']['doors'].values())
                frame.locator('.home-shortcuts [data-home-scroll="todayKitchen"]').click()
                expect(frame.locator('#todayKitchen')).to_be_focused()
                for selector in ('#dailyBalance', '#expirySummary', '#homeRecommendation', '#homePlans',
                                 '#homeBudget', '#homeSupplements', '#homeMonthly', '#homeGrowth', '#homeConnections'):
                    item = frame.locator(selector)
                    item.scroll_into_view_if_needed()
                    expect(item).to_be_visible()
                    no_overflow(frame)
                for selector, button, expected_selector in (
                    ('#homePlans', '[data-workflow="plan"]', '[data-wf-form="plan"]'),
                    ('#homeBudget', '[data-workflow="budget"]', '[data-wf-form="budget"]'),
                    ('#homeSupplements', '[data-workflow="supplements"]', '[data-wf-form="supplement"]'),
                    ('#homeMonthly', '[data-workflow="monthly"]', '.workflow-month'),
                    ('#homeGrowth', '[data-workflow="book"]', '#journalGoal'),
                    ('#homeGrowth', '[data-workflow="rewards"]', '[data-reward="tile"]'),
                    ('#homeGrowth', '[data-workflow="decor"]', '[data-wf-form="theme"]'),
                    ('#homeConnections', '[data-workflow="photos"]', '[data-wf="readPhotos"]')):
                    frame.locator(selector+' '+button).first.click()
                    expect(frame.locator('#tray '+expected_selector)).to_be_visible()
                    no_overflow(frame)
                    close(frame)
                status = frame.locator('#homeConnections details.home-data-status')
                status.locator('summary').click()
                expect(status).to_contain_text('공식')
                expect(status).to_contain_text('연결 전')
                expect(status).to_contain_text('자동 동기화는 지원하지')
                if mode == 'app' and width == 390 and not opaque:
                    home_status = frame.locator('#homeRecommendation [data-stock-status]')
                    expected_status = home_status.get_attribute('data-stock-status')
                    home_status_text = home_status.inner_text()
                    tap_door(page, frame, 'freshRight')
                    lcd_status = frame.locator('#fridgeDisplays [data-lcd="freshRight"] [data-lcd-stock-status]')
                    expect(lcd_status).to_be_visible()
                    expect(lcd_status).to_have_attribute('data-lcd-stock-status', expected_status)
                    if expected_status == 'shortage':
                        count = re.search(r'(\d+)종', home_status_text)[1]
                        expect(lcd_status).to_contain_text('부족 '+count+'종')
                    elif expected_status == 'check':
                        expect(lcd_status).to_contain_text('수량 확인')
                    else:
                        expect(lcd_status).to_contain_text('수량 충족')
                    tap_door(page, frame, 'freshRight')
                if opaque:
                    assert frame.evaluate('KitchenJournal.status') == 'temporary'
                    expect(frame.locator('#homeStorageNotice')).to_be_visible()
                    expect(status).to_contain_text('임시 세션')
                    # A trusted touch must leave the newly opened sheet alive
                    # after the compatibility click (the former retarget bug).
                    item = frame.locator('[data-item="spice0"]')
                    item.scroll_into_view_if_needed()
                    item.tap()
                    page.wait_for_timeout(350)
                    expect(frame.locator('#ingredientForm')).to_be_visible()
                    form = frame.locator('#ingredientForm')
                    form.locator('[name="quantity"]').fill('9작은술')
                    form.locator('[name="expiry"]').fill('2026-12-07')
                    form.locator('[name="opened"]').fill(DAY)
                    form.locator('[type="submit"]').tap()
                    item_data = next(i for i in envelope(frame)['world']['items'] if i['id'] == 'spice0')
                    assert (item_data['quantity'], item_data['expiry'], item_data['opened']) == ('9작은술', '2026-12-07', DAY)
                    close(frame)
                frame.evaluate('window.scrollTo(0,0)')
                dock(frame)
                page.screenshot(path=str(output/f'{mode}-{width}-{"opaque" if opaque else "native"}.png'), full_page=True)
                report['profiles'].append({'mode': mode, 'width': width, 'height': height, 'opaque': opaque})
                passed(f'{mode} {width}x{height} {"opaque touch" if opaque else "native"}: home functions reachable, honest connections, no overflow')
                context.close()

            # Plan -> scaled meal -> real inventory -> cancellation/restore.
            context, page, frame = new()
            stock_ui(frame)
            facts(frame)
            plan_id = plan(frame, 3, '2026-11-03')
            before = envelope(frame)
            row = frame.locator(f'.plan-row[data-plan-id="{plan_id}"]')
            expect(row).to_contain_text('3,000원')
            row.locator('[data-wf="logPlan"]').click()
            form = scaled_form(frame, plan_id, 3, '2026-11-03')
            page.screenshot(path=str(output/'plan-three-portions-confirm.png'), full_page=True)
            form.locator('[type="submit"]').click()
            after = envelope(frame)
            meal = after['play']['meals'][0]
            assert meal['day'] == '2026-11-03' and meal['nutrients']['kcal'] == 234
            transaction = next(t for t in after['workflow']['transactions'] if t['mealId'] == meal['id'])
            assert transaction['planId'] == plan_id and transaction['portions'] == 3 and transaction['active']
            assert len(transaction['deductions']) == 5
            for name, expected in {'계란': '3개', '양파': '1.25개', '식용유': '7작은술', '간장': '7작은술', '밥': '7공기'}.items():
                actual_item = next(item for item in after['world']['items'] if item['name'] == name)
                assert quantity(actual_item['quantity']) == quantity(expected), actual_item
            assert frame.locator('#journalDay').input_value() == '2026-11-03'
            view_plans(frame, '2026-11-03')
            row = frame.locator(f'.plan-row[data-plan-id="{plan_id}"]')
            expect(row).to_contain_text('기록 완료')
            assert row.locator('[data-wf="logPlan"]:enabled').count() == 0
            row.locator('[data-wf="planMeal"]').click()
            frame.locator(f'[data-remove-meal="{meal["id"]}"]').click()
            frame.locator('[data-wf="confirmCancelMeal"]').click()
            canceled = envelope(frame)
            assert canceled['world'] == before['world']
            assert canceled['play']['meals'] == []
            view_plans(frame, '2026-11-03')
            frame.locator(f'.plan-row[data-plan-id="{plan_id}"] [data-wf="logPlan"]').click()
            scaled_form(frame, plan_id, 3, '2026-11-03')
            go(frame, 'nutrition')
            frame.locator('[data-undo-meal]').click()
            restored = envelope(frame)
            assert restored == after, 'Restore must exactly recover world, meal, transaction and awards'
            passed('three-portion plan preserves its date, scales all uses/nutrients/cost and restores exact inventory/meal transaction')

            # Deleting a plan never destroys or strands an existing meal.
            view_plans(frame, '2026-11-03')
            frame.locator(f'.plan-row[data-plan-id="{plan_id}"] [data-wf="removePlan"]').click()
            assert not envelope(frame)['workflow']['plans']
            go(frame, 'nutrition')
            frame.locator('#journalDay').fill('2026-11-03')
            frame.locator('#journalDay').dispatch_event('change')
            frame.locator(f'[data-wf="editMeal"][data-arg="{meal["id"]}"]').click()
            form = frame.locator('#workflowMealForm')
            expect(form).to_be_visible()
            form.locator('[name="protein"]').fill('16')
            form.locator('[type="submit"]').click()
            edited = envelope(frame)
            assert edited['play']['meals'][0]['nutrients']['protein'] == 16
            assert edited['world'] == after['world']
            passed('removing a plan retains its already-recorded meal and permits a nonduplicating meal edit')
            context.close()

            # Shared stock is a single budget across two recipes/plans.
            context, page, frame = new('widget')
            stock_ui(frame, {'계란': '4개', '양파': '0.5개', '식용유': '2작은술', '간장': '10작은술', '밥': '2공기'})
            first = plan(frame, 2, DAY, 'lunch')
            second = plan(frame, 3, DAY, 'dinner')
            before_world = envelope(frame)['world']
            frame.locator(f'#tray [data-wf="planShopping"][data-arg="{DAY}"]').click()
            actual = {r['name']: quantity(r['quantity']) for r in envelope(frame)['workflow']['shopping']}
            assert actual == {'계란': (Fraction(1), '개'), '양파': (Fraction(3, 4), '개'),
                              '식용유': (Fraction(3), '작은술'), '밥/즉석밥': (Fraction(3), '공기')}, actual
            assert envelope(frame)['world'] == before_world
            snapshot = envelope(frame)['workflow']['shopping']
            view_plans(frame, DAY)
            frame.locator(f'#tray [data-wf="planShopping"][data-arg="{DAY}"]').click()
            assert envelope(frame)['workflow']['shopping'] == snapshot
            passed('two plans aggregate five portions and deduct shared stock once; recomputing shopping is idempotent and never consumes inventory')
            context.close()

            # Quantity and expiry are independent uncertainty. Neither may be
            # promoted to verified available stock or a made-up purchase amount.
            context, page, frame = new()
            stock_ui(frame)
            go(frame, 'inventory')
            frame.locator('#tray [data-wf="item"][data-arg="egg"]').click()
            form = frame.locator('#ingredientForm')
            form.locator('[name="expiry"]').fill('')
            form.locator('[type="submit"]').click()
            plan(frame, 1)
            before_world = envelope(frame)['world']
            frame.locator(f'#tray [data-wf="planShopping"][data-arg="{DAY}"]').click()
            assert not any(row['name'] == '계란' for row in envelope(frame)['workflow']['shopping'])
            expect(frame.locator('#tray .workflow-feedback')).to_contain_text('구매 전 확인: 계란')
            expect(frame.locator('#tray .workflow-feedback')).to_contain_text('구매량을 확정하지 않아요')
            assert envelope(frame)['world'] == before_world
            view_plans(frame, DAY)
            frame.locator('#tray [data-wf="logPlan"]').click()
            egg_usage = [row for row in usage(frame) if row['name'] == '계란']
            assert egg_usage and all(not row['checked'] for row in egg_usage), egg_usage
            passed('an otherwise sufficient lot without a printed date remains an unchecked confirmation item with no fabricated shopping amount')
            context.close()

            # No model mutations: a complete visible goal -> meal -> ticket -> reward journey.
            context, page, frame = new()
            frame.evaluate('(keys)=>keys.forEach(k=>localStorage.setItem(k,"SENTINEL-"+k))', ORIGINAL_KEYS)
            stock_ui(frame)
            close(frame)
            frame.locator('#dailyBalance').click()
            frame.locator('#tray [data-wf="targets"],#tray [data-workflow="targets"]').first.click()
            form = frame.locator('[data-wf-form="targets"]')
            for name, value in {'carb': '230', 'protein': '70', 'fat': '60'}.items():
                form.locator(f'[name="{name}"]').fill(value)
            form.locator('[type="submit"]').click()
            go(frame, 'book')
            frame.locator('#journalGoal').select_option('nutrition')
            assert envelope(frame)['play']['goal'] == 'nutrition'
            facts(frame)
            frame.locator('#tray [data-wf="logMeal"]').click()
            form = frame.locator('#workflowMealForm')
            assert form.locator('[name="day"]').input_value() == DAY
            assert all(row['checked'] for row in usage(frame))
            form.locator('[type="submit"]').click()
            summary = frame.evaluate('KitchenJournal.summary("2026-11-01")')
            assert summary['goal']['value'] == summary['goal']['target'] == 1
            assert summary['tickets'] == 1 and summary['cooked'] == ['recipe-1']
            close(frame)
            expect(frame.locator('#homeGrowth [role="progressbar"]')).to_have_attribute('aria-valuenow', '1')
            frame.locator('#homeGrowth [data-workflow="rewards"]').click()
            frame.locator('#tray [data-reward="tile"]').click()
            reward = envelope(frame)['play']
            assert reward['owned'] == ['tile'] and reward['equipped']['frozenLeft'] == 'tile'
            assert frame.evaluate('KitchenJournal.summary().tickets') == 0
            frame.locator('#tray [data-see-fridge]').click()
            expect(frame.locator('.fridge-charm.is-interior[data-charm="tile"]')).to_be_visible()
            expect(frame.locator('#homeGrowth')).to_contain_text('세라믹 타일')
            page.screenshot(path=str(output/'goal-meal-reward-earned.png'), full_page=True)
            passed('visible goal selection -> entered recipe facts -> actual meal -> first-recipe ticket -> equipped visible reward, entirely through controls')

            # Home budget, supplement and calendar reflect real records and stay separate.
            go(frame, 'budget')
            form = frame.locator('[data-wf-form="budget"]')
            form.locator('[name="budget"]').fill('400000')
            form.locator('[type="submit"]').click()
            form = frame.locator('[data-wf-form="expense"]')
            for name, value in {'day': DAY, 'name': '실제 장보기', 'amount': '700'}.items():
                form.locator(f'[name="{name}"]').fill(value)
            form.locator('[type="submit"]').click()
            go(frame, 'supplements')
            form = frame.locator('[data-wf-form="supplement"]')
            for name, value in {'name': '내 비타민', 'amount': '제품 표시량', 'schedule': '내가 정한 저녁', 'remaining': '30정'}.items():
                form.locator(f'[name="{name}"]').fill(value)
            form.locator('[name="ingredients"]').fill('비타민D')
            form.locator('[type="submit"]').click()
            close(frame)
            frame.locator('#homeSupplements [data-home-supplement]').check()
            supplement = envelope(frame)['workflow']['supplements'][0]
            assert supplement['days'] == [DAY] and supplement['amount'] == '제품 표시량'
            assert frame.evaluate('KitchenJournal.summary().nutrients.carb.value') == 10
            expect(frame.locator('#homeBudget [data-home-budget]')).to_contain_text('399,300')
            expect(frame.locator('#homeMonthly .home-month-stats')).to_contain_text('700')
            assert envelope(frame)['workflow']['expenses'][0]['amount'] == 700
            frame.locator('#homeMonthly [data-workflow="monthly"]').click()
            expect(frame.locator('.workflow-month')).to_be_visible()
            assert frame.locator('.workflow-month>div').count() == 30
            close(frame)
            page.screenshot(path=str(output/'entered-records-home.png'), full_page=True)
            passed('home shows actual remaining budget, supplement schedule/check and November records without adding estimated meal cost or supplement nutrients')

            # Honest zero/unknown distinction and same actual recipe on LCD/home.
            close(frame)
            recommended_id = frame.locator('#homeRecommendation [data-home-recipe]').get_attribute('data-home-recipe')
            facts(frame, {'kcal': '0', 'carb': '0', 'protein': '0', 'fat': '0', 'cost': '0'}, recommended_id)
            close(frame)
            assert frame.locator('#homeRecommendation [data-home-recipe]').get_attribute('data-home-recipe') == recommended_id
            expect(frame.locator('#homeRecommendation [data-home-kcal]')).to_have_text('0 kcal')
            expect(frame.locator('#homeRecommendation [data-home-cost]')).to_have_text('0원')
            home_name = frame.locator('#homeRecommendation [data-home-recipe] h3').inner_text()
            tap_door(page, frame, 'freshRight')
            lcd = frame.locator('#fridgeDisplays [data-lcd="freshRight"]')
            expect(lcd).to_be_visible()
            expect(lcd).to_have_attribute('data-recommended-recipe', recommended_id)
            expect(lcd.locator('.lcd-recipe')).to_have_text(home_name)
            stock_status = frame.locator('#homeRecommendation [data-stock-status]').get_attribute('data-stock-status')
            expect(lcd.locator('[data-lcd-stock-status]')).to_have_attribute('data-lcd-stock-status', stock_status)
            assert stock_status == 'ready', 'Known compatible dated stock should be ready in this fixture'
            expect(lcd.locator('[data-lcd-stock-status]')).to_contain_text('수량 충족')
            expect(lcd.locator('.lcd-recipe-detail')).not_to_contain_text('수량 확인')
            expect(lcd.locator('.lcd-nutrition-cost')).to_contain_text('0 kcal')
            expect(lcd.locator('.lcd-nutrition-cost')).to_contain_text('0원')
            tap_door(page, frame, 'freshRight')
            facts(frame, {'kcal': '', 'carb': '', 'protein': '', 'fat': '', 'cost': ''}, recommended_id)
            close(frame)
            expect(frame.locator('#homeRecommendation [data-home-kcal]')).to_contain_text('미입력')
            expect(frame.locator('#homeRecommendation [data-home-cost]')).to_contain_text('미입력')
            assert frame.evaluate('KitchenJournal.summary().nutrients.carb.value') == 10
            passed('recommendation LCD and home use the same recipe; explicitly entered zero remains zero and missing nutrition/cost remains unknown')

            snapshot = envelope(frame)
            page.reload()
            frame.wait_for_function('window.KitchenHome&&window.KitchenWorkflows')
            assert envelope(frame) == snapshot
            assert frame.evaluate('(keys)=>keys.every(k=>localStorage.getItem(k)==="SENTINEL-"+k)', ORIGINAL_KEYS)
            passed('real-form meal, theme/reward, budget, supplements and original app key sentinels survive exact native reload')
            context.close()

            # Actual touch plan execution in each restrictive mobile wrapper width.
            for mode, width, height in (('app', 320, 660), ('widget', 390, 844)):
                context, page, frame = new(mode, width, height, True)
                stock_ui(frame)
                facts(frame)
                plan_id = plan(frame, 3, DAY)
                close(frame)
                frame.locator(f'#homePlans [data-wf="logPlan"][data-arg="{plan_id}"]').tap()
                page.wait_for_timeout(350)
                form = scaled_form(frame, plan_id, 3, DAY)
                form.locator('[type="submit"]').tap()
                assert envelope(frame)['play']['meals'][0]['nutrients']['carb'] == 30
                no_overflow(frame)
                assert frame.evaluate('KitchenJournal.status') == 'temporary'
                close(frame)
                expect(frame.locator('#homePlans')).to_contain_text('기록 완료')
                assert frame.locator(f'#homePlans [data-wf="logPlan"][data-arg="{plan_id}"]').count() == 0
                passed(f'{mode} opaque touch {width}px: home plan records three real portions with threefold inventory and nutrition')
                context.close()

            # An old envelope must keep date, arbitrary units, coordinates and extras.
            legacy_world = json.loads((repo/'tests/fixtures/miniature-legacy-world-v1.json').read_text())
            legacy_world['items'][0].update(expiry='2000-01-01', quantity='125ml', x=.173, y=.743)
            legacy_play = {'version': 1, 'meals': [], 'targets': {k: None for k in ('kcal', 'carb', 'protein', 'fat', 'fiber', 'water')},
                           'discovered': [], 'awarded': [], 'owned': [], 'equipped': {'frozenLeft': None, 'frozenRight': None},
                           'goal': 'collection', 'plateLabel': '우리 집 부엌'}
            legacy = {'version': 1, 'world': legacy_world, 'play': legacy_play, 'retainedFutureField': {'owner': 'unchanged'}}
            raw = json.dumps(legacy, ensure_ascii=False)
            context, page, frame = new(init='if(localStorage.getItem('+json.dumps(KEY)+')===null)localStorage.setItem('+json.dumps(KEY)+','+json.dumps(raw)+')')
            assert envelope(frame)['world'] == legacy_world
            assert envelope(frame)['play'] == legacy_play
            assert envelope(frame)['retainedFutureField'] == legacy['retainedFutureField']
            go(frame, 'settings')
            form = frame.locator('[data-wf-form="targets"]')
            form.locator('[name="carb"]').fill('230')
            form.locator('[type="submit"]').click()
            snapshot = envelope(frame)
            close(frame)
            page.reload()
            frame.wait_for_function('window.KitchenHome&&window.KitchenWorkflows')
            assert envelope(frame) == snapshot
            assert snapshot['world'] == legacy_world
            passed('version-one legacy date, quantity, positions and extra envelope fields remain intact through a real save/reload')
            context.close()
            assert not errors, errors
            passed('no JavaScript exceptions in the exercised real journeys')
        except Exception as error:
            report['failures'].append({'message': str(error), 'trace': traceback.format_exc()})
            try:
                page.screenshot(path=str(output/'failure.png'), full_page=True)
                (output/'failure-state.json').write_text(json.dumps(envelope(frame), ensure_ascii=False, indent=2)+'\n')
                (output/'failure-tray.txt').write_text(frame.locator('#tray').inner_text())
            except Exception:
                pass
            raise
        finally:
            current = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
            report['inputs_unchanged'] = current == hashes
            if current != hashes:
                report['failures'].append({'message': 'Input generated pages changed during verification', 'current_sha256': current})
            report['javascript_errors'] = errors
            (output/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            browser.close()
            server.shutdown()
    if report['failures']:
        raise SystemExit(1)
    print(json.dumps({'passed': len(report['passed']), 'failed': len(report['failures'])}))


if __name__ == '__main__':
    main()
