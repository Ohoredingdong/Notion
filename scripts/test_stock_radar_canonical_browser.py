"""Visual geometry smoke test for canonical investment radar (local HTTP server on :8765)."""
from __future__ import annotations
import json
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("RADAR_BASE_URL", "http://127.0.0.1:8765/").rstrip("/") + "/"
MAX_CARD_HEIGHT = 150

def main():
    with sync_playwright() as browser_api:
        launch_options = {"headless": True}
        if os.environ.get("BROWSER_EXECUTABLE"):
            launch_options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        browser = browser_api.chromium.launch(**launch_options)
        for width, height in [(1629, 929), (1366, 768)]:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            # The second URL was published by mistake; it must open the same canonical page.
            page.goto(BASE + "stock-radar-dashboard.html?stock=005930#home", wait_until="domcontentloaded")
            page.wait_for_url("**/stock-value-radar.html?stock=005930#home", timeout=20000)
            page.wait_for_function(
                "() => document.querySelectorAll('.fx-v5-markets .nr-index').length===4"
                " && document.querySelector('.fx-sent-v9-flag-svg')!==null"
                " && document.querySelector('.fx-v5-main')!==null",
                timeout=30000,
            )
            info = page.evaluate("""() => {
                const box = sel => {
                    const el = document.querySelector(sel);
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return {x:r.x, y:r.y, width:r.width, height:r.height, bottom:r.bottom};
                };
                return {
                    url: location.pathname + location.search + location.hash,
                    row: box('.fx-v5-marketline'),
                    title: box('.fx-v5-markettitle'),
                    cards: [...document.querySelectorAll('.fx-v5-markets .nr-index')].map(el => {
                      const b=el.getBoundingClientRect();return {width:b.width,height:b.height,bottom:b.bottom};
                    }),
                    flag: box('.fx-sent-v9-flag-svg'),
                    sentiment: box('.fx-sent-v9'),
                    main: box('.fx-v5-main'),
                    home: box('.fx-v5-home'),
                };
            }""")
            print("CANONICAL_RADAR_GEOMETRY", json.dumps({"viewport":width,"metrics":info},ensure_ascii=False))
            assert info["row"] and info["row"]["height"] <= MAX_CARD_HEIGHT, "Oversized market strip"
            assert info["flag"] and 0 < info["flag"]["width"] <= 32 and 0 < info["flag"]["height"] <= 28, "Unstyled giant flag"
            assert all(0 < c["height"] <= MAX_CARD_HEIGHT for c in info["cards"]), "Full-screen market card overlay"
            assert info["main"] and info["main"]["y"] >= info["row"]["bottom"]-3, "Market strip overlaps research workspace"
            assert info["main"]["width"] >= width * 0.8, "Workspace unexpectedly narrow"
            page.close()
        browser.close()
    print("CANONICAL_RADAR_VISUAL_SMOKE_PASSED")

if __name__ == "__main__":
    main()
