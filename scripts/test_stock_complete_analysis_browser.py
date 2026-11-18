"""Read-only UI regression; local static server, no collection or dispatch."""
import os
from playwright.sync_api import sync_playwright, expect
URL=os.environ.get('RADAR_TEST_URL','http://127.0.0.1:8765/stock-radar-research.html')
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width,height in [(1440,1000),(390,844)]:
        page=browser.new_page(viewport={'width':width,'height':height})
        page.goto(URL)
        frame=page.frame_locator('iframe')
        opener=frame.get_by_role('button',name='선택 기업 전체 분석')
        opener.click()
        dialog=frame.get_by_role('dialog',name='선택 기업 전체 분석')
        expect(dialog).to_be_visible()
        expect(dialog).to_contain_text('아직 미연결')
        for label in ['01 거시 환경','02 산업 분석','03 기업 질적 분석','04 재무 · 가치 분석','05 공시 · 자본 변화','06 차트 · 기술 분석','07 종합 · 진입 판단']:
            dialog.get_by_role('button',name=label,exact=True).click()
            assert dialog.locator('[data-rnd-panel]:visible').count()==1
            rect=dialog.bounding_box()
            assert rect['x']>=0 and rect['x']+rect['width']<=width+1
        expect(dialog).to_contain_text('매수후보 판단 보류')
        dialog.get_by_role('button',name='05 공시 · 자본 변화').click()
        for label in ['전체 공시','계약 · 수주','CB · BW','자사주','M&A · 분할']:
            dialog.get_by_role('tab',name=label,exact=True).click()
            assert dialog.locator('[role=tabpanel]:visible').count()==1
        dialog.get_by_role('button',name='전체 분석 닫기').click()
        expect(dialog).not_to_be_visible()
        expect(opener).to_be_visible()
        row=frame.locator('.fx-row[data-nr-select]').nth(1)
        expect(row).to_be_visible()
        name=row.locator('strong').inner_text()
        row.click()
        opener.click()
        expect(dialog.locator('.rnd-header h2')).to_contain_text(name)
        dialog.get_by_role('button',name='05 공시 · 자본 변화').click()
        dialog.get_by_role('tab',name='전체 공시',exact=True).press('End')
        expect(dialog.get_by_role('tab',name='M&A · 분할')).to_have_attribute('aria-selected','true')
        dialog.get_by_role('button',name='전체 분석 닫기').press('Escape')
        expect(dialog).not_to_be_visible()
        print(f'PASS native wrapper, seven sections, five tabs, mobile bounds, close/Escape: {width}x{height}')
        page.close()
    browser.close()
