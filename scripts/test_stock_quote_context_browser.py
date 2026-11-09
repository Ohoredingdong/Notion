"""UI provenance/connection checks only. No price extraction, trades or model updates."""
from __future__ import annotations
import argparse, json, os, re
from pathlib import Path
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base',default='http://127.0.0.1:8765/stock-value-radar.html')
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--provider-check',action='store_true')
    args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'views':[],'failures':[],
            'limits':['Viewport proxies, not physical devices/Notion app.', 'Provider UI availability is not real-time, overnight or executable-price verification.']}
    def check(condition, message):
        if not condition: raise AssertionError(message)
    with sync_playwright() as pw:
        exe=os.environ.get('BROWSER_EXECUTABLE')
        browser=pw.chromium.launch(headless=True,**({'executable_path':exe} if exe else {}))
        for width,height in ((1440,900),(1245,768),(1180,640),(390,844),(360,640)):
            ctx=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
            ctx.route('https://s3.tradingview.com/**',lambda route:route.abort())
            page=ctx.new_page(); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
            view={'width':width,'height':height}
            try:
                page.goto(args.base+'?stock=NVDA',wait_until='domcontentloaded',timeout=60000)
                page.wait_for_function("() => document.querySelector('.fx-v5-stocktitle')?.textContent.includes('NVDA') && !!document.querySelector('[data-quote-context]')",timeout=60000)
                page.evaluate('() => document.fonts.ready')
                date=page.evaluate("() => window.StockRadarV2Bridge.snapshot().data.raw.companies.find(c=>c.symbol==='NVDA').price_session")
                label=page.locator('[data-quote-session]'); check(label.is_visible(),'date hidden')
                check(date+' 정규장 종가' in label.inner_text(),'not the exact saved session')
                state=page.evaluate("() => JSON.stringify(window.StockRadarV2Bridge.snapshot().data.raw)")
                geometry=page.evaluate("""() => {
                  const box=s=>document.querySelector(s).getBoundingClientRect();
                  const row=box('.fx-world-marketline'), main=box('.fx-v5-main'),quote=box('.fx-v5-quote'),card=box('.fx-v5-cockpit');
                  return {gap:main.top-row.bottom,overflow:document.documentElement.scrollWidth-innerWidth,quoteFits:quote.left>=card.left&&quote.right<=card.right+1};
                }""")
                check(abs(geometry['gap']-12)<1,'12px accepted spacing changed')
                check(geometry['overflow']<=1,'page horizontal overflow')
                check(geometry['quoteFits'],'quote leaves card')
                view['geometry']=geometry; view['session_label']=label.inner_text()
                page.screenshot(path=str(args.out/f'quote-context-{width}x{height}.png'))
                button=page.locator('[data-quote-view]').first;button.click()
                dialog=page.locator('.radar-quote-dialog[open]');dialog.wait_for()
                check('지연 가능' in dialog.inner_text(),'delay caveat missing')
                check('야간거래' in dialog.inner_text(),'overnight scope missing')
                page.wait_for_function("() => document.querySelector('.radar-quote-load-status')?.textContent.includes('불러오지 못했습니다')",timeout=15000)
                link=dialog.locator('.radar-quote-source-link').get_attribute('href')
                check(link=='https://www.tradingview.com/symbols/NASDAQ-NVDA/','wrong provider symbol')
                check(page.evaluate("() => JSON.stringify(window.StockRadarV2Bridge.snapshot().data.raw)")==state,'research source mutated')
                page.keyboard.press('Escape');check(page.locator('.radar-quote-dialog').count()==0,'dialog not cleaned up')
                check(not errors,'runtime error: '+str(errors))
                view['passed']=True
            except Exception as exc:
                view['error']=str(exc);report['failures'].append(f'{width}: {exc}')
                page.screenshot(path=str(args.out/f'failure-{width}.png'))
            finally:
                report['views'].append(view);ctx.close()
        if args.provider_check:
            ctx=browser.new_context(viewport={'width':1245,'height':768});page=ctx.new_page()
            provider={'data_exported':False,'real_time_verified':False,'overnight_verified':False}
            try:
                page.goto(args.base+'?stock=NVDA',wait_until='domcontentloaded',timeout=60000)
                page.wait_for_selector('[data-quote-view]',timeout=60000)
                page.locator('[data-quote-view]').first.click()
                page.wait_for_selector('.radar-quote-provider-host iframe',timeout=30000)
                frame=page.locator('.radar-quote-provider-host iframe').element_handle().content_frame()
                frame.wait_for_function("() => /NVDA|NVIDIA|엔비디아/i.test(document.body.innerText) && /[0-9]+[.,][0-9]{2}/.test(document.body.innerText)",timeout=45000)
                provider['instrument_and_quote_ui_visible']=True
                provider['provider_host']=frame.url.split('/')[2]
                page.screenshot(path=str(args.out/'provider-nvda-visible.png'))
            except Exception as exc:
                provider['instrument_and_quote_ui_visible']=False
                provider['error']=type(exc).__name__
                report['failures'].append('Real provider quote view not established: '+type(exc).__name__)
                page.screenshot(path=str(args.out/'provider-unverified.png'))
            finally:
                report['provider']=provider;ctx.close()
        browser.close()
    (args.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('QUOTE_CONTEXT_BROWSER',json.dumps(report,ensure_ascii=False))
    if report['failures']:raise SystemExit(1)
if __name__=='__main__':main()
