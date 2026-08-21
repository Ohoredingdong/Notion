#!/usr/bin/env python3
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

BASE = "https://www.reb.or.kr"
LIST_URL = BASE + "/reb/na/ntt/selectNttList.do?mi=9565&bbsId=1154"
OUT = Path("real-estate-pulse-data.json")
REGIONS = ["서울","부산","대구","인천","광주","대전","울산","세종","경기","강원","충북","충남","전북","전남","경북","경남","제주"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; NotionRealEstatePulse/1.0; +https://github.com/Ohoredingdong/Notion)"}


def get(url, **kwargs):
    r = requests.get(url, headers=UA, timeout=30, **kwargs)
    r.raise_for_status()
    return r


def latest_release():
    candidates = []
    for page in range(1, 4):
        url = LIST_URL + (f"&currPage={page}" if page > 1 else "")
        soup = BeautifulSoup(get(url).text, "html.parser")
        for a in soup.find_all("a"):
            title = " ".join(a.stripped_strings)
            m = re.search(r"주간아파트가격동향\((\d{8})기준\)", title)
            if not m:
                continue
            href = a.get("href", "")
            if not href:
                continue
            if href.startswith("javascript:"):
                n = re.search(r"nttSn\D+(\d+)", href)
                if n:
                    href = f"/reb/na/ntt/selectNttInfo.do?mi=9565&bbsId=1154&nttSn={n.group(1)}"
                else:
                    continue
            candidates.append((m.group(1), urljoin(BASE, href)))
    if not candidates:
        raise RuntimeError("REB 주간아파트가격동향 최신 게시물을 찾지 못했습니다.")
    asof, url = max(candidates, key=lambda x: x[0])
    return asof, url


def find_pdf_url(detail_url):
    html = get(detail_url).text
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for tag in soup.find_all(True):
        text = " ".join(tag.stripped_strings)
        attrs = " ".join(str(v) for v in tag.attrs.values())
        blob = f"{text} {attrs}"
        if ".pdf" not in blob.lower() and "file" not in blob.lower():
            continue
        for key in ("href", "data-url", "data-file", "onclick"):
            val = tag.get(key)
            if not val:
                continue
            vals = val if isinstance(val, list) else [val]
            for raw in vals:
                raw = str(raw)
                for pat in (
                    r"(https?://[^'\"\s)]+)",
                    r"(['\"])(/[^'\"]*(?:download|file|fms|atch)[^'\"]*)\1",
                ):
                    for m in re.finditer(pat, raw, re.I):
                        u = m.group(1) if pat.startswith("(https") else m.group(2)
                        candidates.append(urljoin(BASE, u.replace("&amp;", "&")))
                if raw.startswith("/"):
                    candidates.append(urljoin(BASE, raw))
        href = tag.get("href")
        if href and isinstance(href, str) and href != "#" and not href.lower().startswith("javascript:"):
            candidates.append(urljoin(BASE, href))

    # Prefer links clearly associated with a PDF attachment.
    candidates = list(dict.fromkeys(candidates))
    scored = sorted(candidates, key=lambda u: (("pdf" in u.lower()), ("down" in u.lower() or "file" in u.lower())), reverse=True)
    for u in scored:
        try:
            r = get(u, allow_redirects=True)
        except Exception:
            continue
        if r.content[:4] == b"%PDF" or "application/pdf" in r.headers.get("content-type", "").lower():
            return r.url, r.content

    # Some REB pages expose the attachment URL only inside inline scripts.
    patterns = [
        r"['\"]([^'\"]*(?:FileDown|fileDown|download)[^'\"]*)['\"]",
        r"['\"]([^'\"]+\.pdf(?:\?[^'\"]*)?)['\"]",
    ]
    for pat in patterns:
        for raw in re.findall(pat, html, flags=re.I):
            u = urljoin(detail_url, raw.replace("&amp;", "&"))
            try:
                r = get(u, allow_redirects=True)
            except Exception:
                continue
            if r.content[:4] == b"%PDF" or "application/pdf" in r.headers.get("content-type", "").lower():
                return r.url, r.content
    raise RuntimeError("최신 REB 보도자료에서 PDF 첨부파일을 찾지 못했습니다.")


def pdf_text(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    if len(text) < 500:
        raise RuntimeError("PDF 텍스트 추출량이 너무 적습니다.")
    return text


def section(text, mode):
    # REB releases consistently use these headings, but allow spacing variations.
    if mode == "sale":
        starts = ["주간 아파트 매매가격 동향", "매매가격 동향", "매매가격지수 변동률"]
        ends = ["주간 아파트 전세가격 동향", "전세가격 동향"]
    else:
        starts = ["주간 아파트 전세가격 동향", "전세가격 동향", "전세가격지수 변동률"]
        ends = ["주간 아파트 월세", "주간아파트가격동향 요약", "붙임"]
    pos = -1
    for s in starts:
        p = text.find(s)
        if p >= 0 and (pos < 0 or p < pos):
            pos = p
    if pos < 0:
        return text
    end = len(text)
    for e in ends:
        p = text.find(e, pos + 20)
        if p >= 0:
            end = min(end, p)
    return text[pos:end]


def parse_region_values(text, mode):
    sec = section(text, mode)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in sec.splitlines() if ln.strip()]
    result = {}
    previous = {}

    # First pass: region and weekly values occurring on the same extracted line.
    for region in REGIONS:
        candidates = []
        for i, line in enumerate(lines):
            if not re.search(rf"(^|\s){re.escape(region)}($|\s)", line):
                continue
            window = line
            # PDF extraction sometimes wraps the numeric cells to the following line.
            if i + 1 < len(lines) and len(re.findall(r"[-+]?\d+\.\d+", window)) < 2:
                window += " " + lines[i + 1]
            nums = [float(x) for x in re.findall(r"(?<!\d)([-+]?\d+\.\d+)(?!\d)", window)]
            nums = [x for x in nums if -5 <= x <= 5]
            if nums:
                candidates.append(nums)
        # Prefer a row containing at least two weekly values; the last one is current.
        good = [x for x in candidates if len(x) >= 2]
        chosen = good[0] if good else (candidates[0] if candidates else [])
        if chosen:
            result[region] = chosen[-1]
            previous[region] = chosen[-2] if len(chosen) >= 2 else None

    return result, previous


def published_date(detail_html):
    m = re.search(r"등록일\s*</?[^>]*>.*?(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})", detail_html, re.S)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})", detail_html)
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else datetime.now().strftime("%Y-%m-%d")


def main():
    current = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    asof_raw, detail_url = latest_release()
    detail_html = get(detail_url).text
    pdf_url, pdf_bytes = find_pdf_url(detail_url)
    text = pdf_text(pdf_bytes)
    sale, sale_prev = parse_region_values(text, "sale")
    lease, lease_prev = parse_region_values(text, "lease")

    missing_sale = [r for r in REGIONS if r not in sale]
    missing_lease = [r for r in REGIONS if r not in lease]
    print("Latest:", asof_raw, detail_url)
    print("PDF:", pdf_url)
    print("sale:", sale)
    print("lease:", lease)
    if missing_sale or missing_lease:
        print("missing sale:", missing_sale, file=sys.stderr)
        print("missing lease:", missing_lease, file=sys.stderr)
        raise RuntimeError("17개 시도 전체를 공식 PDF에서 파싱하지 못해 기존 JSON을 유지합니다.")

    prev_base = current.get("baseRate", {"value": 2.75, "previous": 2.50, "changedAt": "2026-07-16"})
    data = {
        "source": "Korea Real Estate Board / Bank of Korea",
        "sourceUrl": detail_url,
        "asOf": f"{asof_raw[:4]}-{asof_raw[4:6]}-{asof_raw[6:]}",
        "published": published_date(detail_html),
        "baseRate": prev_base,
        "regions": [
            {
                "name": r,
                "sale": round(sale[r], 2),
                "salePrev": round(sale_prev[r], 2) if sale_prev[r] is not None else None,
                "lease": round(lease[r], 2),
                "leasePrev": round(lease_prev[r], 2) if lease_prev[r] is not None else None,
            }
            for r in REGIONS
        ],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("updated", OUT)


if __name__ == "__main__":
    main()
