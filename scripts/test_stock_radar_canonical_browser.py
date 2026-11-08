"""Visual geometry smoke test for canonical investment radar (local HTTP server on :8765)."""
from __future__ import annotations
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/"
# User refined the previous oversized cards: content-driven height and exactly 12px gap.
# Keep both size bounds, visible-edge checks and all overflow protections.
MIN_CARD_HEIGHT = 128
MAX_CARD_HEIGHT = 156
MIN_WORKSPACE_GAP = 12


def main():
    with sync_playwright() as browser_api:
        browser = browser_api.chromium.launch(headless=True)
        for width, height in [(1629, 929), (1366, 768)]:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            # The second URL was published by mistake; it must open the same canonical page.
            page.goto(BASE + "stock-radar-dashboard.html?stock=005930#home", wait_until="domcontentloaded")
            page.wait_for_url("**/stock-value-radar.html?stock=005930#home", timeout=20000)
            page.wait_for_function(
                "() => document.querySelectorAll('.fx-worldflow').length===1"
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
                    title: box('.fx-worldflow-head'),
                    cards: [...document.querySelectorAll('.fx-worldflow,.fx-v5-marketline>.fx-sent-v9')].map(el => {
                      const b=el.getBoundingClientRect();return {width:b.width,height:b.height,bottom:b.bottom};
                    }),
                    flag: box('.fx-sent-v9-flag-svg'),
                    sentiment: box('.fx-sent-v9'),
                    main: box('.fx-v5-main'),
                    home: box('.fx-v5-home'),
                };
            }""")
            print("CANONICAL_RADAR_GEOMETRY", json.dumps({"viewport":width,"metrics":info},ensure_ascii=False))
            assert info["row"] and MIN_CARD_HEIGHT <= info["row"]["height"] <= MAX_CARD_HEIGHT, "Market strip does not fit the readable content-height contract"
            assert info["flag"] and 0 < info["flag"]["width"] <= 32 and 0 < info["flag"]["height"] <= 28, "Unstyled giant flag"
            assert len(info["cards"])==2 and all(MIN_CARD_HEIGHT <= c["height"] <= MAX_CARD_HEIGHT for c in info["cards"]), "Full-screen or compressed market card"
            actual_bottom = max(info["row"]["bottom"], *(c["bottom"] for c in info["cards"]))
            assert info["main"] and abs(info["main"]["y"] - actual_bottom - MIN_WORKSPACE_GAP) <= .75, "Visible market cards consume the requested 12px workspace gap"
            assert info["main"]["width"] >= width * 0.8, "Workspace unexpectedly narrow"
            assert info["main"]["bottom"] <= height + 1, "Desktop analysis workspace falls outside the viewport"
            page.close()
        browser.close()
    print("CANONICAL_RADAR_VISUAL_SMOKE_PASSED")


if __name__ == "__main__":
    main()
