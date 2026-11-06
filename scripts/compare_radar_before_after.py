"""Compare protected radar panels under identical genuine candidate data.

Only the requested market-strip replacement is intentional. Home header,
workspace geometry and pixels retain 4px / 12%; detail keeps its full-page gate.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright


def changed_pixels(a, b, output):
    aa, bb = a.convert('RGB'), b.convert('RGB')
    size = (max(aa.width, bb.width), max(aa.height, bb.height))
    left, right = Image.new('RGB', size, 'white'), Image.new('RGB', size, 'white')
    left.paste(aa, (0, 0)); right.paste(bb, (0, 0))
    diff = ImageChops.difference(left, right)
    diff.save(output)
    mask = diff.convert('L').point(lambda px: 255 if px > 20 else 0)
    pixels = mask.histogram()[255]
    return round(100 * pixels / (size[0] * size[1]), 2), pixels, size[0] * size[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', default='http://127.0.0.1:8776')
    parser.add_argument('--after', default='http://127.0.0.1:8765')
    parser.add_argument('--real-data', default='.')
    parser.add_argument('--out', default='radar-universe-evidence')
    args = parser.parse_args()
    data_root = Path(args.real_data).resolve()
    out = Path(args.out); out.mkdir(exist_ok=True)
    report = {'note': 'Both pages use identical genuine candidate repository data files, read-only',
              'intentional_region': 'Home .fx-v5-marketline only; every other home/detail region retains 4px / 12% gates',
              'screens': [], 'failures': []}

    def intercepted(route):
        path = unquote(urlsplit(route.request.url).path).lstrip('/')
        file = (data_root / path).resolve()
        if path.endswith(('.json', '.jsonl')) and file.is_relative_to(data_root) and file.is_file():
            route.fulfill(status=200, body=file.read_bytes(), content_type='application/json' if path.endswith('.json') else 'application/x-ndjson')
        else:
            route.continue_()

    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        try:
            for name, width, height, screen in (('home-desktop', 1440, 900, 'home'),
                                                ('detail-desktop', 1440, 900, 'stockdetail'),
                                                ('home-mobile', 390, 844, 'home'),
                                                ('detail-mobile', 390, 844, 'stockdetail')):
                measurements, paths = [], []
                for stage, base in (('before', args.before), ('after', args.after)):
                    context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme='light',
                                                  reduced_motion='reduce', service_workers='block')
                    context.route('**/*', intercepted)
                    page = context.new_page()
                    url = base + '/stock-value-radar.html' + ('?stock=005930&screen=stockdetail' if screen == 'stockdetail' else '')
                    try:
                        page.goto(url, wait_until='domcontentloaded')
                        page.wait_for_function('() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length', timeout=45000)
                        selector = '.fx-v5-marketline' if screen == 'home' else '.fx-detail-upper'
                        page.locator(selector).wait_for(timeout=15000)
                        info = page.evaluate("""screen => {
                          const box = selector => {
                            const el=document.querySelector(selector);if(!el)return null;
                            const r=el.getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,w:r.width,h:r.height};
                          };
                          const main=box('.fx-v5-main');
                          const children=['.fx-v5-main>.fx-list-panel','.fx-v5-central','.fx-v5-aside'].map(selector=>{
                            const b=box(selector);return b&&main?{selector,x:b.x-main.x,y:b.y-main.y,w:b.w,h:b.h}:null;
                          });
                          return {bounds:box(screen==='home'?'.fx-v5-main':'.fx-detail-upper'),
                            market:box('.fx-v5-marketline'),header:box('.fx-topbar'),source:box('#source-status'),children,
                            viewport:innerWidth};
                        }""", screen)
                        image = out / (stage + '-' + name + '.png')
                        page.screenshot(path=str(image), full_page=True, animations='disabled')
                        paths.append(image); measurements.append(info)
                    finally:
                        context.close()
                before, after = measurements
                if not before['bounds'] or not after['bounds']:
                    report['failures'].append(name + ': missing approved panel')
                    continue
                deltas = {axis: round(abs(before['bounds'][axis] - after['bounds'][axis]), 2) for axis in ('x', 'y', 'w', 'h')}
                protected = {}
                market_delta = 0
                if screen == 'home':
                    if not before['market'] or not after['market']:
                        report['failures'].append(name + ': missing intended market region')
                        continue
                    market_delta = after['market']['h'] - before['market']['h']
                    # Translate only by the actual requested market-height change.
                    deltas['y'] = round(abs(after['bounds']['y'] - before['bounds']['y'] - market_delta), 2)
                    protected['marketPosition'] = {axis: round(abs(before['market'][axis] - after['market'][axis]), 2) for axis in ('x', 'y', 'w')}
                    before_gap = before['bounds']['y'] - before['market']['y'] - before['market']['h']
                    after_gap = after['bounds']['y'] - after['market']['y'] - after['market']['h']
                    protected['marketWorkspaceGap'] = {'gap': round(abs(after_gap - before_gap), 2)}
                    for key in ('header', 'source'):
                        if not before[key] or not after[key]:
                            report['failures'].append(name + ': missing protected ' + key)
                        else:
                            protected[key] = {axis: round(abs(before[key][axis] - after[key][axis]), 2) for axis in ('x', 'y', 'w', 'h')}
                    for index, (left, right) in enumerate(zip(before['children'], after['children'])):
                        if not left or not right:
                            report['failures'].append(f'{name}: missing protected workspace panel {index}')
                        else:
                            protected[left['selector']] = {axis: round(abs(left[axis] - right[axis]), 2) for axis in ('x', 'y', 'w', 'h')}
                    for label, difference in protected.items():
                        if max(difference.values()) > 4:
                            report['failures'].append(f'{name}: protected {label} geometry shift {difference}')
                if max(deltas.values()) > 4:
                    report['failures'].append(f'{name}: unexpected baseline geometry shift {deltas}')
                regions = []
                with Image.open(paths[0]) as a, Image.open(paths[1]) as b:
                    if screen == 'home':
                        # Header and the entire remaining page each keep 12%.
                        crops = [('header', a.crop((0, 0, a.width, round(before['market']['y']))),
                                  b.crop((0, 0, b.width, round(after['market']['y'])))),
                                 ('workspace', a.crop((0, round(before['bounds']['y']), a.width, a.height)),
                                  b.crop((0, round(after['bounds']['y']), b.width, b.height)))]
                        changed = pixels = 0
                        for label, left, right in crops:
                            pct, count, size = changed_pixels(left, right, out / ('diff-' + name + '-' + label + '.png'))
                            changed += count; pixels += size
                            regions.append({'region': label, 'pixelDifferencePct': pct, 'beforeSize': left.size, 'afterSize': right.size})
                            if pct > 12:
                                report['failures'].append(f'{name}: protected {label} changed {pct}%')
                        change = round(100 * changed / pixels, 2)
                    else:
                        # Keep the original full-page detail comparison.
                        if a.size != b.size:
                            change = 100.0
                        else:
                            change, _, _ = changed_pixels(a, b, out / ('diff-' + name + '.png'))
                        if change > 12:
                            report['failures'].append(f'{name}: {change}% changed on the protected detail view')
                    size_changed = a.size != b.size
                report['screens'].append({'view': name, 'before': str(paths[0]), 'after': str(paths[1]),
                                          'geometryDelta': deltas, 'protectedGeometry': protected,
                                          'intentionalMarketHeightDelta': round(market_delta, 2),
                                          'pixelDifferencePct': change, 'protectedPixels': regions, 'sizeChanged': size_changed})
        finally:
            browser.close()
    (out / 'before-after-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('STOCK_RADAR_BEFORE_AFTER', len(report['screens']), 'views', len(report['failures']), 'failures')
    if report['failures']:
        raise SystemExit(chr(10).join(report['failures']))


if __name__ == '__main__':
    main()
