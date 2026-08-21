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
UA = {"User-Agent": "Mozilla/5.0 (compatible; NotionRealEstatePulse/1.1; +https://github.com/Ohoredingdong/Notion)"}


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
    return max(candidates, key=lambda x: x[0])


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

    candidates = list(dict.fromkeys(candidates))
    scored = sorted(
        candidates,
        key=lambda u: (("pdf" in u.lower()), ("down" in u.lower() or "file" in u.lower())),
        reverse=True,
    )
    for u in scored:
        try:
            r = get(u, allow_redirects=True)
        except Exception:
            continue
        if r.content[:4] == b"%PDF" or "application/pdf" in r.headers.get("content-type", "").lower():
            return r.url, r.content

    for pat in (
        r"['\"]([^'\"]*(?:FileDown|fileDown|download)[^'\"]*)['\"]",
        r"['\"]([^'\"]+\.pdf(?:\?[^'\"]*)?)['\"]",
    ):
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


def appendix_one(text):
    # The press release mentions '붙임 1' once in the contents and again at the
    # actual appendix. Choose the LAST occurrence so we land on the real table.
    pat = re.compile(r"붙임\s*1\s*[:：]?\s*주간\s*아파트\s*시도별\s*변동률\s*통계표", re.I)
    matches = list(pat.finditer(text))
    if not matches:
        raise RuntimeError("공식 PDF에서 '붙임 1 주간 아파트 시도별 변동률 통계표'를 찾지 못했습니다.")
    start = matches[-1].start()
    tail = text[start:]
    next_appendix = re.search(r"\n\s*붙임\s*2\b", tail, re.I)
    return tail[: next_appendix.start()] if next_appendix else tail


def split_sale_lease(appendix):
    sale_head = re.search(r"□?\s*매매가격\s*변동률", appendix)
    lease_head = re.search(r"□?\s*전세가격\s*변동률", appendix)
    if not sale_head or not lease_head:
        raise RuntimeError("붙임 1에서 매매/전세 변동률 구간을 찾지 못했습니다.")
    if sale_head.start() < lease_head.start():
        sale = appendix[sale_head.end():lease_head.start()]
        lease = appendix[lease_head.end():]
    else:
        lease = appendix[lease_head.end():sale_head.start()]
        sale = appendix[sale_head.end():]
    return sale, lease


def region_pattern(region):
    # pypdf often extracts '서울' as '서 울', '경기' as '경 기', etc.
    return re.compile(r"^\s*" + r"\s*".join(map(re.escape, region)) + r"(?:\s|$)")


def starts_region(line):
    return any(region_pattern(r).search(line) for r in REGIONS)


def parse_appendix_table(section_text):
    lines = [re.sub(r"[\u00a0\t]+", " ", ln).strip() for ln in section_text.splitlines() if ln.strip()]
    values = {}
    previous = {}

    for region in REGIONS:
        rp = region_pattern(region)
        row_numbers = None
        for i, line in enumerate(lines):
            if not rp.search(line):
                continue
            window = line
            nums = re.findall(r"(?<!\d)([-+]?\d+(?:\.\d+)?)(?!\d)", window)
            # If PDF extraction wrapped one row, append the next line only when
            # that next line clearly is not another region row.
            if len(nums) < 3 and i + 1 < len(lines) and not starts_region(lines[i + 1]):
                window += " " + lines[i + 1]
                nums = re.findall(r"(?<!\d)([-+]?\d+(?:\.\d+)?)(?!\d)", window)
            parsed = [float(x) for x in nums if -100 <= float(x) <= 100]
            if len(parsed) >= 2:
                row_numbers = parsed
                break
        if row_numbers:
            # Appendix rows are cumulative columns followed by weekly columns.
            # The rightmost value is the current week; the one before it is the
            # immediately previous published week.
            values[region] = row_numbers[-1]
            previous[region] = row_numbers[-2]

    return values, previous


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

    appendix = appendix_one(text)
    sale_text, lease_text = split_sale_lease(appendix)
    sale, sale_prev = parse_appendix_table(sale_text)
    lease, lease_prev = parse_appendix_table(lease_text)

    missing_sale = [r for r in REGIONS if r not in sale]
    missing_lease = [r for r in REGIONS if r not in lease]
    print("Latest:", asof_raw, detail_url)
    print("PDF:", pdf_url)
    print("sale:", sale)
    print("lease:", lease)
    if missing_sale or missing_lease:
        print("missing sale:", missing_sale, file=sys.stderr)
        print("missing lease:", missing_lease, file=sys.stderr)
        raise RuntimeError("붙임 1 통계표에서 17개 시도 전체를 파싱하지 못해 기존 JSON을 유지합니다.")

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
                "salePrev": round(sale_prev[r], 2),
                "lease": round(lease[r], 2),
                "leasePrev": round(lease_prev[r], 2),
            }
            for r in REGIONS
        ],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("updated", OUT)


if __name__ == "__main__":
    main()
