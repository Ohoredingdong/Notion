from pathlib import Path

shared = '<link rel="stylesheet" href="./assets/life-town-v2.css" />'
script = '<script src="./assets/life-town-controls-v2.js"></script>'

configs = {
    'market-events.html': ('market-events-v2.html', '''
<style id="lt-v2-overrides">
:root{--bg:#fff;--panel:#fff;--line:#e7e7ea;--line-soft:#f0f0f2;--soft:#f7f7f8;--soft-2:#fafafa;--text:#111113;--sub:#6e6e73;--muted:#a1a1a6;--green:#34c759;--green-deep:#218a3d;--green-soft:rgba(52,199,89,.08);--red:#ff3b30;--red-soft:rgba(255,59,48,.07);--amber:#ad8600;--amber-soft:rgba(255,204,0,.11);--blue:#007aff;--blue-soft:rgba(0,122,255,.08);--shadow:0 12px 32px rgba(0,0,0,.055),0 1px 2px rgba(0,0,0,.035)}
body{padding:6px;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,Pretendard,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}.root{width:min(100%,680px)!important}.widget{position:relative;border-radius:24px;padding:18px 17px 14px;box-shadow:var(--shadow);overflow:hidden}.widget:before{content:"";position:absolute;left:18px;right:18px;top:0;height:1px;background:linear-gradient(90deg,transparent,#b8b8bd 25%,#f6f6f8 50%,#b8b8bd 75%,transparent);opacity:.8}.title{font-size:19px;font-weight:760;letter-spacing:-.045em}.subtitle{font-size:10px;color:var(--muted);margin-top:5px}.update{height:26px;border-radius:999px;background:#fff}.hero{margin-top:14px;border-radius:16px;background:#fafafa;padding:14px}.hero-label{font-size:11px;color:var(--sub)}.hero-icon{background:rgba(0,122,255,.07);color:var(--blue)}.impact-tag{border-color:rgba(255,204,0,.25);background:rgba(255,204,0,.10);color:#8d7000}.summary{gap:8px}.sum{border-radius:14px;background:#fff}.sum-icon{background:#f3f3f5;color:var(--sub)}.board{border-radius:16px}.col-title{color:var(--text)}.col-title-wrap svg{color:var(--blue)}.controls{display:none!important}.retry{background:#fff}.hero-country{font-weight:700;color:var(--text)}
</style>'''),
    'commodities-dashboard.html': ('commodities-dashboard-v2.html', '''
<style id="lt-v2-overrides">
:root{--bg:#fff;--panel:#fff;--line:#e7e7ea;--soft:#f7f7f8;--soft2:#fafafa;--text:#111113;--sub:#6e6e73;--muted:#a1a1a6;--green:#34c759;--greenbg:rgba(52,199,89,.08);--red:#ff3b30;--redbg:rgba(255,59,48,.07);--blue:#007aff;--accent:#007aff;--shadow:0 12px 32px rgba(0,0,0,.055),0 1px 2px rgba(0,0,0,.035)}
body{padding:6px;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,Pretendard,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}.widget{position:relative;width:min(100%,840px);border-radius:24px;padding:18px;box-shadow:var(--shadow);overflow:hidden}.widget:before{content:"";position:absolute;left:18px;right:18px;top:0;height:1px;background:linear-gradient(90deg,transparent,#b8b8bd 25%,#f6f6f8 50%,#b8b8bd 75%,transparent);opacity:.8}.title{font-size:19px;font-weight:760;letter-spacing:-.045em}.subtitle{font-size:10px;color:var(--muted)}.layout{gap:10px}.list-panel,.detail{border-radius:16px}.asset{border-radius:12px}.asset.active{background:rgba(0,122,255,.055);border-color:rgba(0,122,255,.16)}.asset-change{padding:3px 6px}.detail-kicker{color:var(--blue)}.chart-wrap{height:140px}.stats{border-radius:13px}.line{stroke:var(--blue)}.last-dot{fill:var(--blue)}.chart{color:var(--blue)}.quote-krw{margin-top:5px;font-size:9px;color:var(--sub);font-weight:620}.data-warning{color:var(--red);font-weight:700}
</style>'''),
    'fear-greed-dashboard.html': ('market-mood-v2.html', '''
<style id="lt-v2-overrides">
:root{--bg:#fff;--panel:#fff;--line:#e7e7ea;--soft:#f7f7f8;--soft2:#fafafa;--text:#111113;--sub:#6e6e73;--muted:#a1a1a6;--shadow:0 12px 32px rgba(0,0,0,.055),0 1px 2px rgba(0,0,0,.035);--fear1:#ff3b30;--fear2:#ff3b30;--neutral:#ffcc00;--greed:#34c759;--greed2:#34c759;--control-bg:#fff;--control-line:#e7e7ea}
body{padding:6px;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,Pretendard,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}.widget-root{width:min(100%,430px)!important}.widget{position:relative;height:auto;min-height:0;max-height:none;border-radius:24px;padding:18px 17px 14px;box-shadow:var(--shadow);overflow:hidden}.widget:before{content:"";position:absolute;left:18px;right:18px;top:0;height:1px;background:linear-gradient(90deg,transparent,#b8b8bd 25%,#f6f6f8 50%,#b8b8bd 75%,transparent);opacity:.8}.title{font-size:19px;font-weight:760;letter-spacing:-.045em}.subtitle{font-size:10px;color:var(--muted)}.tabs{border-radius:12px;background:#f7f7f8}.tab{height:30px;border-radius:9px}.score{font-size:46px}.gauge-track{height:8px}.gauge-thumb{width:18px;height:18px;border-width:4px}.chart{min-height:128px;gap:8px}.bar-shell{height:78px;max-width:24px}.footer{height:auto;min-height:38px;max-height:none}.controls{display:none!important}
</style>''')
}

for src, (dst, override) in configs.items():
    text = Path(src).read_text(encoding='utf-8')
    if shared not in text:
        text = text.replace('</head>', shared + '\n' + override + '\n</head>')
    else:
        text = text.replace('</head>', override + '\n</head>')
    if script not in text:
        text = text.replace('</body>', script + '\n</body>')

    if src == 'market-events.html':
        text = text.replace('<div class="title">Market Events</div>', '<div class="title">마켓 이벤트</div>')
        text = text.replace('<div class="subtitle">시장 주요 이벤트 레이더</div>', '<div class="subtitle">한국·미국·일본·유럽 주요 경제 일정을 한눈에</div>')
        text = text.replace(
            '<div class="meta"><span class="chip" id="heroDate"></span><span class="chip" id="heroTime"></span></div>',
            '<div class="meta"><span class="chip hero-country" id="heroCountry"></span><span class="chip" id="heroDate"></span><span class="chip" id="heroTime"></span></div>'
        )
        text = text.replace(
            "const flags={US:'🇺🇸',KR:'🇰🇷',JP:'🇯🇵',GB:'🇬🇧',DE:'🇩🇪',FR:'🇫🇷',CN:'🇨🇳',EU:'🇪🇺'};",
            "const flags={US:'🇺🇸',KR:'🇰🇷',JP:'🇯🇵',GB:'🇬🇧',DE:'🇩🇪',FR:'🇫🇷',CN:'🇨🇳',EU:'🇪🇺'};const countryNames={US:'미국',KR:'한국',JP:'일본',GB:'영국',DE:'독일',FR:'프랑스',CN:'중국',EU:'유로존'};"
        )
        text = text.replace(
            "<span class=\"country\">${flags[e.country]||e.country||''}</span>${escapeHtml(e.title_ko||e.title||'')}",
            "<span class=\"country\">${flags[e.country]||''} ${escapeHtml(countryNames[e.country]||e.country||'')}</span>${escapeHtml(e.title_ko||e.title||'')}"
        )
        text = text.replace(
            "document.getElementById('heroTitle').textContent = highlight.title_ko || highlight.title || '주요 이벤트';",
            "const heroCountryName=countryNames[highlight.country]||highlight.country||''; const heroRawTitle=highlight.title_ko||highlight.title||'주요 이벤트'; document.getElementById('heroTitle').textContent = heroCountryName ? `${heroCountryName} ${heroRawTitle}` : heroRawTitle;"
        )
        text = text.replace(
            "document.getElementById('heroDate').innerHTML = `${icons.cal}<span>${escapeHtml(highlight.date_kst || '—')}</span>`;",
            "document.getElementById('heroCountry').innerHTML = `<span>${flags[highlight.country]||''} ${escapeHtml(heroCountryName)}${highlight.currency?` · ${escapeHtml(highlight.currency)}`:''}</span>`; document.getElementById('heroDate').innerHTML = `${icons.cal}<span>${escapeHtml(highlight.date_kst || '—')}</span>`;"
        )

    elif src == 'commodities-dashboard.html':
        text = text.replace('<div class="section-title">Market</div><div class="section-sub">6 assets</div>', '<div class="section-title">원자재</div><div class="section-sub">7개 자산</div>')
        text = text.replace(
            "const order=['금','은','구리','브렌트유','WTI 원유','천연가스'];const groups={'금':'Precious metal','은':'Precious metal','구리':'Industrial metal','브렌트유':'Energy','WTI 원유':'Energy','천연가스':'Energy'};",
            "const order=['금','은','구리','알루미늄','브렌트유','WTI 원유','천연가스'];const groups={'금':'귀금속','은':'귀금속','구리':'산업금속','알루미늄':'산업금속','브렌트유':'에너지','WTI 원유':'에너지','천연가스':'에너지'};"
        )
        text = text.replace(
            '<div class="quote-price" id="detailPrice">—</div><div class="quote-change" id="detailChange">—</div>',
            '<div class="quote-price" id="detailPrice">—</div><div class="quote-change" id="detailChange">—</div><div class="quote-krw" id="detailKrw">—</div>'
        )
        text = text.replace(
            "<div class=\"asset-meta\">${groups[i.name]||''}</div>",
            "<div class=\"asset-meta\">${groups[i.name]||''}${i.unit?` · ${i.unit}`:''}</div>"
        )
        text = text.replace(
            "$('#detailChange').textContent=fmtChange(i.change_pct);$('#detailChange').className='quote-change '+(Number(i.change_pct)>=0?'up':'down');",
            "$('#detailChange').textContent=fmtChange(i.change_pct);$('#detailChange').className='quote-change '+(Number(i.change_pct)>=0?'up':'down');$('#detailKrw').textContent=i.krw_value?`₩${Number(i.krw_value).toLocaleString('ko-KR',{maximumFractionDigits:2})} / ${i.krw_label||'환산 단위'}`:'원화 환산 —';"
        )
        text = text.replace(
            "$('#updated').textContent=`Data ${fmtDateTime(state.sourceUpdated)}`;$('#timeInfo').textContent=`Source · Yahoo Finance · Data ${fmtDateTime(state.sourceUpdated)} KST · Hourly`",
            "const ageMin=(Date.now()-state.sourceUpdated.getTime())/60000;const delayed=Number.isFinite(ageMin)&&ageMin>180;$('#updated').innerHTML=delayed?`<span class=\"data-warning\">업데이트 지연</span> · ${fmtDateTime(state.sourceUpdated)}`:`Data ${fmtDateTime(state.sourceUpdated)}`;$('#timeInfo').textContent=delayed?`Source · Yahoo Finance · ${fmtDateTime(state.sourceUpdated)} KST · 업데이트 지연`:`Source · Yahoo Finance · Data ${fmtDateTime(state.sourceUpdated)} KST · Hourly`"
        )

    elif src == 'fear-greed-dashboard.html':
        text = text.replace('<div class="title">Market Mood</div>', '<div class="title">시장 심리</div>')
        text = text.replace('<div class="subtitle">시장 온도</div>', '<div class="subtitle">한국 · 미국 · Crypto</div>')
        text = text.replace('>Korea</button>', '>한국</button>').replace('>US</button>', '>미국</button>')

    Path(dst).write_text(text, encoding='utf-8')
