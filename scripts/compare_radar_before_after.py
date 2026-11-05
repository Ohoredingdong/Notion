"""Compare unchanged approved radar panels before/after under the same real data.

Expected new stock directory/news screens are intentionally different; home and
detail screenshot differences are recorded and layout geometry must remain intact.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from urllib.parse import urlsplit,unquote
import json
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--before",default="http://127.0.0.1:8776")
    parser.add_argument("--after",default="http://127.0.0.1:8765")
    parser.add_argument("--real-data",default=".")
    parser.add_argument("--out",default="radar-universe-evidence")
    args=parser.parse_args()
    data_root=Path(args.real_data).resolve()
    out=Path(args.out);out.mkdir(exist_ok=True)
    report={"note":"Both pages use identical genuine candidate repository data files, read-only",
            "screens":[],"failures":[]}
    def intercepted(route):
        url=urlsplit(route.request.url)
        path=unquote(url.path).lstrip("/")
        file=(data_root/path).resolve()
        if (path.endswith((".json",".jsonl")) and
            file.is_relative_to(data_root) and file.is_file()):
            route.fulfill(status=200,body=file.read_bytes(),
                          content_type="application/json" if path.endswith(".json") else "application/x-ndjson")
        else:
            route.continue_()
    with sync_playwright() as play:
        browser=play.chromium.launch(headless=True)
        try:
            for name,width,height,screen in (("home-desktop",1440,900,"home"),
                                              ("detail-desktop",1440,900,"stockdetail"),
                                              ("home-mobile",390,844,"home"),
                                              ("detail-mobile",390,844,"stockdetail")):
                measurements=[]
                paths=[]
                for stage,base in (("before",args.before),("after",args.after)):
                    context=browser.new_context(viewport={"width":width,"height":height},
                                                color_scheme="light",reduced_motion="reduce",
                                                service_workers="block")
                    context.route("**/*",intercepted)
                    page=context.new_page()
                    url=base+"/stock-value-radar.html"+("?stock=005930&screen=stockdetail" if screen=="stockdetail" else "")
                    try:
                        page.goto(url,wait_until="domcontentloaded")
                        page.wait_for_function("""() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length""",timeout=45000)
                        selector=".fx-v5-marketline" if screen=="home" else ".fx-detail-upper"
                        page.locator(selector).wait_for(timeout=15000)
                        info=page.evaluate("""(selector)=>{
                          const b=document.querySelector(selector)?.getBoundingClientRect();
                          const row=[...document.querySelectorAll(selector===' .fx-v5-marketline'?'.fx-v5-markets .nr-index':'.fx-detail-upper>.fx-panel')];
                          return {bounds:b&&{x:b.x,y:b.y,w:b.width,h:b.height},
                            viewport:innerWidth,panelCount:row.length};
                        }""",selector)
                        image=out/(stage+"-"+name+".png")
                        page.screenshot(path=str(image),full_page=True,animations="disabled")
                        paths.append(image);measurements.append(info)
                    finally:
                        context.close()
                before,after=measurements
                if not before["bounds"] or not after["bounds"]:
                    report["failures"].append(name+": missing approved panel")
                    continue
                deltas={axis:round(abs(before["bounds"][axis]-after["bounds"][axis]),2)
                        for axis in ("x","y","w","h")}
                if max(deltas.values())>4:
                    report["failures"].append(f"{name}: unexpected baseline geometry shift {deltas}")
                with Image.open(paths[0]) as a,Image.open(paths[1]) as b:
                    aa,bb=a.convert("RGB"),b.convert("RGB")
                    if aa.size!=bb.size:
                        change=100.0
                        diff_size=True
                    else:
                        diff=ImageChops.difference(aa,bb)
                        diff.save(out/("diff-"+name+".png"))
                        mask=diff.convert("L").point(lambda px:255 if px>20 else 0)
                        change=round(100*mask.histogram()[255]/(aa.width*aa.height),2)
                        diff_size=False
                report["screens"].append({"view":name,"before":str(paths[0]),"after":str(paths[1]),
                                         "geometryDelta":deltas,"pixelDifferencePct":change,
                                         "sizeChanged":diff_size})
                if change>12:
                    report["failures"].append(f"{name}: {change}% changed on an approved, otherwise untouched view")
        finally:
            browser.close()
    (out/"before-after-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STOCK_RADAR_BEFORE_AFTER",len(report["screens"]),"views",len(report["failures"]),"failures")
    if report["failures"]:
        raise SystemExit("\n".join(report["failures"]))


if __name__=="__main__":
    main()
