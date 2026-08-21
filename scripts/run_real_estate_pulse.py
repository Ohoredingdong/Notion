#!/usr/bin/env python3
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import update_real_estate_pulse as core

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
})


def session_get(url, **kwargs):
    r = SESSION.get(url, timeout=35, **kwargs)
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
    if wanted in normalize_text(BeautifulSoup(html, "html.parser").get_text(" ")):
        return url
    return None


def latest_release():
    # REB sometimes omits the board rows for stateless/bot-like requests.
    # Establish the same session flow a browser uses before opening the board.
    try:
        session_get(f"{core.BASE}/reb/main.do")
    except Exception:
        pass

    candidates = []
    title_re = re.compile(r"주간\s*아파트\s*가격\s*동향\s*\(\s*(\d{8})\s*기준\s*\)")

    for page in range(1, 6):
        url = core.LIST_URL + (f"&currPage={page}" if page > 1 else "")
        html = session_get(url).text
        soup = BeautifulSoup(html, "html.parser")

        # Normal path: title and detail URL are exposed in an anchor/onclick.
        for a in soup.find_all("a"):
            text = " ".join(a.stripped_strings)
            m = title_re.search(text)
            if not m:
                continue
            asof = m.group(1)
            attrs = " ".join(str(v) for v in a.attrs.values())
            blob = f"{a.get('href', '')} {attrs}"
            ids = re.findall(r"nttSn\D{0,20}(\d{5,9})", blob, flags=re.I)
            ids += re.findall(r"(?<!\d)(\d{5,7})(?!\d)", blob)
            for ntt in dict.fromkeys(ids):
                detail = validate_detail(asof, ntt)
                if detail:
                    candidates.append((asof, detail))
                    break

        # Fallback path: locate the title in raw HTML and inspect nearby markup.
        for m in title_re.finditer(html):
            asof = m.group(1)
            chunk = html[max(0, m.start() - 2500): min(len(html), m.end() + 2500)]
            ids = re.findall(r"nttSn\D{0,30}(\d{5,9})", chunk, flags=re.I)
            ids += re.findall(r"(?<!\d)(\d{5,7})(?!\d)", chunk)
            for ntt in dict.fromkeys(ids):
                detail = validate_detail(asof, ntt)
                if detail:
                    candidates.append((asof, detail))
                    break

        # Some board templates put the post id in hidden form controls rather
        # than an anchor. Search row-like elements containing the title.
        for node in soup.find_all(["tr", "li", "div"]):
            text = " ".join(node.stripped_strings)
            m = title_re.search(text)
            if not m:
                continue
            asof = m.group(1)
            blob = str(node)
            ids = re.findall(r"nttSn\D{0,30}(\d{5,9})", blob, flags=re.I)
            ids += re.findall(r"(?<!\d)(\d{5,7})(?!\d)", blob)
            for ntt in dict.fromkeys(ids):
                detail = validate_detail(asof, ntt)
                if detail:
                    candidates.append((asof, detail))
                    break

    if not candidates:
        raise RuntimeError("REB 세션형 목록에서도 최신 주간아파트가격동향 게시물을 찾지 못했습니다.")
    return max(candidates, key=lambda x: x[0])


# Make every downstream Excel/PDF request reuse the established browser session.
core.get = session_get
core.latest_release = latest_release
core.main()
