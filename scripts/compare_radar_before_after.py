"""Compare protected radar panels using identical genuine data.

The user authorized readable market height and a 24px desktop / 20px mobile
workspace gap. Normalize ONLY those two layout inputs on the baseline before
comparing protected workspace geometry/pixels. Preserve original screenshots,
4px geometry tolerance, 12% pixel tolerance, and full-page detail checks.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

MEASURE = """screen => {
 const box=selector=>{const el=document.querySelector(selector);if(!el)return null;
   const r=el.getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,w:r.width,h:r.height}};
 const main=box('.fx-v5-main');
 const children=['.fx-v5-main>.fx-list-panel','.fx-v5-central','.fx-v5-aside'].map(selector=>{
   const b=box(selector);return b&&main?{selector,x:b.x-main.x,y:b.y-main.y,w:b.w,h:b.h}:null});
 const cards=[...document.querySelectorAll('.fx-worldflow,.fx-world-marketline>.fx-sent-v9')].map(e=>{
   const r=e.getBoundingClientRect();return {bottom:r.bottom+scrollY}});
 return {bounds:box(screen==='home'?'.fx-v5-main':'.fx-detail-upper'),
   market:box('.fx-v5-marketline'),header:box('.fx-topbar'),source:box('#source-status'),children,cards};
}"""


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
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    report = {'note': 'Identical genuine repository JSON for both views, read-only',
              'intentional_region': 'Market row content height and 24px desktop / 20px mobile gap only',
              'protected_contract': 'Baseline normalized by ONLY those two top-layout inputs; header, workspace and detail keep 4px / 12% gates',
              'screens': [], 'failures': []}

    def intercepted(route):
        path = unquote(urlsplit(route.request.url).path).lstrip('/')
        file = (data_root / path).resolve()
        if path.endswith(('.json', '.jsonl')) and file.is_relative_to(data_root) and file.is_file():
            route.fulfill(status=200, body=file.read_bytes(), content_type='application/json' if path.endswith('.json') else 'application/x-ndjson')
        else:
            route.continue_()

    def geometry_delta(left, right):
        return {key: round(abs(left[key] - right[key]), 2) for key in ('x', 'y', 'w', 'h')}

    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        try:
            for name, width, height, screen in (('home-desktop', 1440, 900, 'home'),
                                              ('detail-desktop', 1440, 900, 'stockdetail'),
                                              ('home-mobile', 390, 844, 'home'),
                                              ('detail-mobile', 390, 844, 'stockdetail')):
                def capture(stage, base, normalization=None):
                    context = browser.new_context(viewport={'width': width, 'height': height},
                                                  color_scheme='light', reduced_motion='reduce', service_workers='block')
                    context.route('**/*', intercepted)
                    page = context.new_page()
                    url = base + '/stock-value-radar.html' + ('?stock=005930&screen=stockdetail' if screen == 'stockdetail' else '')
                    try:
                        page.goto(url, wait_until='domcontentloaded')
                        page.wait_for_function('() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length', timeout=45000)
                        page.locator('.fx-v5-marketline' if screen == 'home' else '.fx-detail-upper').wait_for(timeout=15000)
                        if normalization is not None:
                            # No workspace CSS, DOM, prices or app state is changed.
                            page.evaluate("""({height,gap})=>{
                              const market=document.querySelector('.fx-v5-marketline');
                              const home=market.parentElement;
                              for(const [key,value] of Object.entries({height:height+'px',flex:'0 0 '+height+'px','min-height':'0','max-height':'none',margin:'0'}))market.style.setProperty(key,value,'important');
                              home.style.setProperty('gap',gap+'px','important');
                            }""", normalization)
                        info = page.evaluate(MEASURE, screen)
                        image = out / (stage + '-' + name + '.png')
                        page.screenshot(path=str(image), full_page=True, animations='disabled')
                        return info, image
                    finally:
                        context.close()

                before, before_path = capture('before', args.before)
                after, after_path = capture('after', args.after)
                if not before['bounds'] or not after['bounds']:
                    report['failures'].append(name + ': missing approved panel')
                    continue
                protected = {}
                reference, reference_path = before, before_path
                normalization = None
                if screen == 'home':
                    if not before['market'] or not after['market']:
                        report['failures'].append(name + ': missing intended market region')
                        continue
                    required_gap = 20 if width <= 850 else 24
                    after_gap = after['bounds']['y'] - after['market']['y'] - after['market']['h']
                    visible_bottom = max(after['market']['y'] + after['market']['h'], *(c['bottom'] for c in after['cards']))
                    if abs(after_gap - required_gap) > .75 or after['bounds']['y'] < visible_bottom + required_gap - .75:
                        report['failures'].append(name + ': requested visible workspace gap not preserved')
                    protected['marketPosition'] = {key: round(abs(before['market'][key] - after['market'][key]), 2) for key in ('x', 'y', 'w')}
                    for key in ('header', 'source'):
                        if not before[key] or not after[key]:
                            report['failures'].append(name + ': missing protected ' + key)
                        else:
                            protected[key] = geometry_delta(before[key], after[key])
                    normalization = {'height': after['market']['h'], 'gap': required_gap}
                    reference, reference_path = capture('normalized-before', args.before, normalization)
                    for index, (left, right) in enumerate(zip(reference['children'], after['children'])):
                        if not left or not right:
                            report['failures'].append(f'{name}: missing protected workspace panel {index}')
                        else:
                            protected[left['selector']] = geometry_delta(left, right)
                    for label, difference in protected.items():
                        if max(difference.values()) > 4:
                            report['failures'].append(f'{name}: protected {label} geometry shift {difference}')
                deltas = geometry_delta(reference['bounds'], after['bounds'])
                if max(deltas.values()) > 4:
                    report['failures'].append(f'{name}: unexpected protected geometry shift {deltas}')
                regions = []
                with Image.open(reference_path) as a, Image.open(after_path) as b:
                    if screen == 'home':
                        crops = [('header', a.crop((0, 0, a.width, round(reference['market']['y']))),
                                  b.crop((0, 0, b.width, round(after['market']['y'])))),
                                 ('workspace', a.crop((0, round(reference['bounds']['y']), a.width, a.height)),
                                  b.crop((0, round(after['bounds']['y']), b.width, b.height)))]
                        changed = pixels = 0
                        for label, left, right in crops:
                            pct, count, size = changed_pixels(left, right, out / ('diff-' + name + '-' + label + '.png'))
                            changed += count
                            pixels += size
                            regions.append({'region': label, 'pixelDifferencePct': pct, 'beforeSize': left.size, 'afterSize': right.size})
                            if pct > 12:
                                report['failures'].append(f'{name}: protected {label} changed {pct}%')
                        change = round(100 * changed / pixels, 2)
                    else:
                        change = 100.0 if a.size != b.size else changed_pixels(a, b, out / ('diff-' + name + '.png'))[0]
                        if change > 12:
                            report['failures'].append(f'{name}: {change}% changed on the protected detail view')
                    size_changed = a.size != b.size
                report['screens'].append({'view': name, 'originalBefore': str(before_path), 'comparisonBefore': str(reference_path),
                                          'after': str(after_path), 'authorizedNormalization': normalization,
                                          'geometryDelta': deltas, 'protectedGeometry': protected,
                                          'pixelDifferencePct': change, 'protectedPixels': regions, 'sizeChanged': size_changed})
        finally:
            browser.close()
    (out / 'before-after-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('STOCK_RADAR_BEFORE_AFTER', len(report['screens']), 'views', len(report['failures']), 'failures')
    if report['failures']:
        raise SystemExit(chr(10).join(report['failures']))


if __name__ == '__main__':
    main()
