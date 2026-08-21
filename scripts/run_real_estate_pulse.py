#!/usr/bin/env python3
import re

import requests
from bs4 import BeautifulSoup

import update_real_estate_pulse as core

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
})


def session_get(url, **kwargs):
    r = SESSION.get(url, timeout=20, **kwargs)
    r.raise_for_status()
    return r


def normalize_text(value):
    return re.sub(r"\s+", "", value or "")


def validate_detail(asof_raw, ntt_sn):
    url = f"{core.BASE}/reb/na/ntt/selectNttInfo.do?mi=9565&bbsId=1154&nttSn={ntt_sn}"
    try:
        html = session_get(url).text
    except Exception:
        return None
    wanted = f"주간아파트가격동향({asof_raw}기준)"
    return url if wanted in normalize_text(BeautifulSoup(html, "html.parser").get_text(" ")) else None


def candidate_post_ids(blob):
    # REB's nttSn values are currently six digits. Restricting the fallback to
    # six digits avoids treating dates/view counts as post ids.
    ids = re.findall(r"nttSn\D{0,30}(\d{5,9})", blob, flags=re.I)
    ids += re.findall(r"(?<!\d)(\d{6})(?!\d)", blob)
    return list(dict.fromkeys(ids))


def latest_release():
    try:
        session_get(f"{core.BASE}/reb/main.do")
    except Exception:
        pass

    candidates = []
    title_re = re.compile(r"주간\s*아파트\s*가격\s*동향\s*\(\s*(\d{8})\s*기준\s*\)")

    # The newest weekly release is on the first page; page 2 is a small safety
    # margin for unusual announcement volume.
    for page in (1, 2):
        url = core.LIST_URL + (f"&currPage={page}" if page > 1 else "")
        html = session_get(url).text
        soup = BeautifulSoup(html, "html.parser")

        for node in soup.find_all(["a", "tr", "li"]):
            text = " ".join(node.stripped_strings)
            m = title_re.search(text)
            if not m:
                continue
            asof = m.group(1)
            for ntt in candidate_post_ids(str(node))[:8]:
                detail = validate_detail(asof, ntt)
                if detail:
                    candidates.append((asof, detail))
                    break

        if candidates:
            continue

        # Raw HTML fallback for templates where the title isn't attached to an
        # anchor in the parsed DOM.
        for m in title_re.finditer(html):
            asof = m.group(1)
            chunk = html[max(0, m.start() - 1800): min(len(html), m.end() + 1800)]
            for ntt in candidate_post_ids(chunk)[:8]:
                detail = validate_detail(asof, ntt)
                if detail:
                    candidates.append((asof, detail))
                    break

    if not candidates:
        raise RuntimeError("REB 세션형 목록에서도 최신 주간아파트가격동향 게시물을 찾지 못했습니다.")
    latest = max(candidates, key=lambda x: x[0])
    print("Latest official REB release:", latest)
    return latest


def fast_discover_rone_excel(asof_raw):
    """Try only strongly Excel-like R-ONE links, then fail fast to PDF.

    R-ONE's report list is dynamic, so a short official-Excel attempt is safer
    than crawling dozens of generic report links. PDF remains the fully official
    fallback and is parsed from its appendix table.
    """
    try:
        session_get(f"{core.BASE}/r-one/portal/main/indexPage.do")
    except Exception:
        pass

    pages = []
    for params in ({}, {"searchKeyword": "전국주택가격동향조사"}, {"searchKeyword": "주간"}):
        try:
            r = session_get(core.RONE_REPORT_URL, params=params)
            pages.append((r.url, r.text))
        except Exception:
            continue

    direct = []
    detail = []
    for page_url, html in pages:
        for url, text in core.urls_from_html(html, page_url):
            blob = f"{url} {text}".lower()
            if ".xlsx" in blob or ".xls" in blob or "엑셀" in text:
                direct.append(url)
            elif "/r-one/portal/bbs/rpt/" in url and "searchBulletinPage.do" not in url:
                if "전국주택" in text or "주간" in text:
                    detail.append(url)

    for detail_url in list(dict.fromkeys(detail))[:8]:
        try:
            r = session_get(detail_url)
        except Exception:
            continue
        for url, text in core.urls_from_html(r.text, r.url):
            blob = f"{url} {text}".lower()
            if ".xlsx" in blob or ".xls" in blob or "엑셀" in text:
                direct.append(url)

    direct = list(dict.fromkeys(direct))
    direct.sort(key=lambda u: ((asof_raw in u), ("xlsx" in u.lower())), reverse=True)
    for url in direct[:12]:
        try:
            r = session_get(url, allow_redirects=True)
        except Exception:
            continue
        if core.is_excel_response(r):
            print("R-ONE Excel candidate:", r.url)
            return r.url, r.content

    raise RuntimeError("R-ONE 주간 Excel 직접 링크를 빠른 탐색에서 찾지 못했습니다.")


# Make every downstream request reuse the established browser session and keep
# Excel as the first source, with the REB PDF appendix as the fallback.
core.get = session_get
core.latest_release = latest_release
core.discover_rone_excel = fast_discover_rone_excel
core.main()
