"""Actual browser geometry and screenshots for the radar home spacing contract.
No mock prices, no rewritten feed, no UI-generated forecast or trading action.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

VIEWPORTS = ((1440, 900), (1366, 768), (1245, 768), (1180, 640),
             (1024, 768), (920, 680), (390, 844), (360, 640))
MEASURE = """() => {
 const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
 const market=document.querySelector('.fx-world-marketline'),world=document.querySelector('.fx-worldflow'),
       sentiment=market?.querySelector('.fx-sent-v9'),main=document.querySelector('.fx-v5-main');
 if(!market||!world||!sentiment||!main)throw Error('Required actual dashboard elements absent');
 const m=box(market),w=box(world),s=box(sentiment),a=box(main);
 const content=[...world.children].filter(e=>e.tagName!=='DIALOG').map(e=>({className:e.className,...box(e)}));
 const tiles=[...world.querySelectorAll('[data-worldflow-index]')].map(e=>({id:e.dataset.worldflowIndex,...box(e),
   value:e.querySelector('[data-worldflow-index-value]')?.textContent,
   overflowing:[...e.children].some(c=>c.scrollWidth>c.clientWidth+1)}));
 return {market:m,world:w,sentiment:s,main:a,content,tiles,
   gap:a.y-Math.max(m.bottom,w.bottom,s.bottom),
   worldOverflow:world.scrollHeight-world.clientHeight,
   horizontalOverflow:document.documentElement.scrollWidth-innerWidth,
   viewport:{width:innerWidth,height:innerHeight},
   worldFeedTimestamp:window.StockRadarV2Bridge?.snapshot()?.data?.worldFlow?.generated_at||null};
}"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8765/stock-value-radar.html')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--capture-only', action='store_true')
    parser.add_argument('--label', default='after')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = {'captured_at': datetime.now(timezone.utc).isoformat(), 'label': args.label,
              'capture_only': args.capture_only, 'source_url': args.base, 'views': [],
              'limitations': ['Desktop/mobile viewports and iframe proxies, not actual Notion app or physical devices.']}
    failures = []

    def record_checks(metrics, errors, width):
        minimum_gap = 20 if width <= 850 else 24
        checks = {
            'protected_workspace_gap': metrics['gap'] >= minimum_gap - .75,
            'all_five_indices_retained': len(metrics['tiles']) == 5,
            'no_clipped_index_text': all(not t['overflowing'] for t in metrics['tiles']),
            'market_content_stays_inside_its_card': all(c['bottom'] <= metrics['world']['bottom'] + .75 for c in metrics['content']),
            'no_market_content_vertical_overflow': metrics['worldOverflow'] <= 1,
            'no_horizontal_page_overflow': metrics['horizontalOverflow'] <= 1,
            'no_browser_runtime_error': not errors,
        }
        if width >= 1180:
            checks['both_top_cards_end_before_main'] = max(metrics['world']['bottom'], metrics['sentiment']['bottom']) + 23 <= metrics['main']['y']
        if width >= 1180 and metrics['viewport']['height'] >= 768:
            checks['desktop_main_fits_available_viewport'] = metrics['main']['bottom'] <= metrics['viewport']['height'] + 1
        return checks

    with sync_playwright() as play:
        executable = os.environ.get('BROWSER_EXECUTABLE')
        browser = play.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
        try:
            for width, height in VIEWPORTS:
                context = browser.new_context(viewport={'width': width, 'height': height},
                                              reduced_motion='reduce', color_scheme='light')
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                view = {'width': width, 'height': height}
                try:
                    page.goto(args.base, wait_until='domcontentloaded', timeout=60000)
                    page.wait_for_function("() => document.querySelectorAll('[data-worldflow-index]').length===5 && !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length", timeout=60000)
                    page.evaluate('() => document.fonts.ready')
                    page.wait_for_timeout(250)
                    metrics = page.evaluate(MEASURE)
                    view['metrics'] = metrics
                    view['checks'] = record_checks(metrics, errors, width)
                    screenshot = args.out / f'{args.label}-{width}x{height}.png'
                    page.screenshot(path=str(screenshot), full_page=False)
                    view['screenshot'] = screenshot.name
                    if not args.capture_only:
                        for key, value in view['checks'].items():
                            if not value:
                                failures.append(f'{width}x{height}: {key}')
                        # Switching country must not collapse the market row or consume its gap.
                        switch = page.locator('[data-fx-sentiment-next]')
                        if switch.count() == 1:
                            switch.click()
                            page.wait_for_timeout(150)
                            switched = page.evaluate(MEASURE)
                            view['switched_gap'] = switched['gap']
                            if switched['gap'] < (20 if width <= 850 else 24) - .75:
                                failures.append(f'{width}: sentiment switch collapsed spacing')
                        page.locator('[data-worldflow-open]').click()
                        dialog = page.locator('.fx-worldflow-dialog[open]')
                        dialog.wait_for()
                        view['source_dialog_count'] = dialog.locator('[data-worldflow-indicator]').count()
                        if view['source_dialog_count'] != 14:
                            failures.append(f'{width}: source observations lost')
                        page.keyboard.press('Escape')
                except Exception as exc:
                    view['exception'] = type(exc).__name__ + ': ' + str(exc)
                    failures.append(f'{width}x{height}: {view["exception"]}')
                    page.screenshot(path=str(args.out / f'{args.label}-{width}-failure.png'))
                finally:
                    report['views'].append(view)
                    context.close()
            # A constrained Notion-size iframe is measured in its own coordinate space.
            if not args.capture_only:
                context = browser.new_context(viewport={'width': 1300, 'height': 800})
                page = context.new_page()
                page.set_content('<iframe title="Radar embed test" style="border:0;width:1245px;height:700px" src="' + args.base + '"></iframe>')
                iframe = page.locator('iframe').element_handle().content_frame()
                iframe.wait_for_function("() => document.querySelectorAll('[data-worldflow-index]').length===5 && !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length", timeout=60000)
                metrics = iframe.evaluate(MEASURE)
                report['iframe'] = metrics
                if metrics['gap'] < 23.25 or metrics['horizontalOverflow'] > 1:
                    failures.append('1245x700 iframe: protected gap or horizontal overflow')
                page.screenshot(path=str(args.out / f'{args.label}-iframe-1245x700.png'))
                context.close()
        finally:
            browser.close()
            report['failures'] = failures
            (args.out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('RADAR_SPACING_GEOMETRY', json.dumps({'label':args.label, 'gaps':[(v['width'],v.get('metrics',{}).get('gap')) for v in report['views']], 'failures': failures}, ensure_ascii=False))
    if failures and not args.capture_only:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
