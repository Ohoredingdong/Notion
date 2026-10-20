#!/usr/bin/env python3
"""Read the latest REB release and its official PDF viewer's text layer.

The public board uses data-id links and RAONK attachments, not direct PDF links.
The document lookup and text endpoints below are the ones used by REB's own
openDocView viewer. No guessed Excel workbook or previous-week column is used.
"""
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE = "https://www.reb.or.kr"
LIST_URL = BASE + "/reb/na/ntt/selectNttList.do?mi=9565&bbsId=1154"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "real-estate-pulse-data.json"
REGIONS = ["서울", "부산", "대구", "인천", "대전", "울산", "전남광주", "세종",
           "경기", "강원", "충북", "충남", "전북", "경북", "경남", "제주"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; NotionRealEstatePulse/2.0)"}
KST = ZoneInfo("Asia/Seoul")


def get(url, **kwargs):
    response = requests.get(url, headers=UA, timeout=35, **kwargs)
    response.raise_for_status()
    return response


def release_candidates(html):
    candidates = []
    for anchor in BeautifulSoup(html, "html.parser").find_all("a"):
        title = re.sub(r"\s+", "", anchor.get_text())
        match = re.search(r"주간아파트가격동향\((\d{8})기준\)", title)
        if not match:
            continue
        stamp = datetime.strptime(match[1], "%Y%m%d").date()
        if stamp > datetime.now(KST).date():
            continue
        identifier = anchor.get("data-id", "")
        href = anchor.get("href", "")
        if re.fullmatch(r"\d+", identifier):
            href = f"/reb/na/ntt/selectNttInfo.do?mi=9565&nttSn={identifier}"
        if "selectNttInfo.do" in href and "nttSn=" in href:
            candidates.append((match[1], urljoin(BASE, href)))
    return candidates


def latest_release():
    candidates = release_candidates(get(LIST_URL).text)
    if not candidates:
        candidates = release_candidates(get(BASE + "/reb/main.do").text)
    if not candidates:
        raise RuntimeError("REB 게시판에서 날짜가 확인된 최신 주간 발표를 찾지 못했습니다.")
    return max(candidates, key=lambda value: value[0])


def published_date(html):
    soup = BeautifulSoup(html, "html.parser")
    for heading in soup.find_all("th"):
        if heading.get_text(strip=True) == "등록일":
            cell = heading.find_next_sibling("td")
            match = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", cell.get_text() if cell else "")
            if match:
                stamp = date(int(match[1]), int(match[2]), int(match[3]))
                if stamp <= datetime.now(KST).date():
                    return stamp.isoformat()
    raise RuntimeError("공식 보도자료의 등록일을 확인하지 못했습니다.")


def appendix_text(detail_html):
    attachments = re.findall(r"RAONKUPLOAD\.AddUploadedFile\(([^;]+)\);", detail_html)
    keys = []
    for attachment in attachments:
        values = re.findall(r"'([^']*)'", attachment)
        if len(values) >= 5 and values[1].lower().endswith(".pdf"):
            keys.append(values[4])
    if len(keys) != 1 or not re.fullmatch(r"[a-zA-Z0-9_-]+", keys[0]):
        raise RuntimeError("최신 발표의 공식 PDF 첨부를 하나로 확인하지 못했습니다.")
    file_key = keys[0]
    lookup = requests.post(BASE + "/reb/docView.do", data={"fileKey": file_key}, headers=UA, timeout=35)
    lookup.raise_for_status()
    result = lookup.json()
    document_id = result.get("docViewId", "")
    if result.get("resultAt") != "Y" or not re.fullmatch(r"[a-zA-Z0-9_-]+", document_id):
        raise RuntimeError("REB 공식 PDF 미리보기가 문서를 반환하지 않았습니다.")
    document_url = BASE + "/docview/v4/documents/" + document_id
    info = get(document_url + "/info").json()
    count = int(info.get("PageCount", 0))
    if info.get("DocumentType") != "PDF" or not 1 <= count <= 40:
        raise RuntimeError("PDF 문서 정보 또는 페이지 수가 예상과 다릅니다.")

    def read_page(index):
        blocks = get(document_url + f"/texts/{index}").json()
        if not isinstance(blocks, list):
            raise RuntimeError("공식 PDF 텍스트 형식이 바뀌었습니다.")
        text = "\n".join(block.get("text", "") for block in blocks)
        compact = re.sub(r"\s+", "", text)
        is_appendix = "붙임1" in compact and "주간아파트시도별" in compact
        return index, text, is_appendix

    with ThreadPoolExecutor(max_workers=4) as pool:
        pages = list(pool.map(read_page, range(count)))
    matches = [(index, text) for index, text, found in pages if found and "매매가격" in text and "전세가격" in text]
    if len(matches) != 1:
        raise RuntimeError("공식 PDF에서 매매·전세 시도별 붙임 1 표를 확인하지 못했습니다.")
    index, text = matches[0]
    return {"text": text, "page": index + 1, "fileKey": file_key,
            "viewerUrl": BASE + "/reb/openDocView.do?fileKey=" + file_key,
            "textSha256": hashlib.sha256(text.encode()).hexdigest()}


def split_sale_lease(text):
    sale = re.search(r"매매가격(?:지수)?\s*변동률", text)
    lease = re.search(r"전세가격(?:지수)?\s*변동률", text)
    if not sale or not lease or sale.start() >= lease.start():
        raise RuntimeError("공식 통계표의 매매/전세 구간을 구분하지 못했습니다.")
    return text[sale.end():lease.start()], text[lease.end():]


def parse_appendix_table(text, asof_raw):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    dates = []
    for line in lines[:8]:
        found = re.findall(r"(?<!\d)(\d{1,2})\.(\d{1,2})(?!\d)", line)
        if len(found) >= 4:
            dates = [(int(month), int(day)) for month, day in found]
            break
    expected = (int(asof_raw[4:6]), int(asof_raw[6:8]))
    if not dates or dates[-1] != expected:
        raise RuntimeError(f"표의 마지막 주간 열이 발표 기준일 {asof_raw}과 다릅니다: {dates}")
    values, previous = {}, {}
    for region in REGIONS:
        pattern = re.compile(r"^" + r"\s*".join(map(re.escape, region)) + r"\s+")
        rows = [pattern.sub("", line) for line in lines if pattern.match(line)]
        if len(rows) != 1:
            raise RuntimeError(f"{region}의 통계 행을 하나로 확인하지 못했습니다.")
        tokens = rows[0].split()
        # Two cumulative columns followed by exactly the dated weekly columns.
        if len(tokens) != len(dates) + 2:
            raise RuntimeError(f"{region}의 열 수가 공식 날짜 머리글과 맞지 않습니다.")
        try:
            current, prior = float(tokens[-1]), float(tokens[-2])
        except ValueError as exc:
            raise RuntimeError(f"{region}의 최신/직전 주간 값이 누락되었습니다.") from exc
        if not (-5 <= current <= 5 and -5 <= prior <= 5):
            raise RuntimeError(f"{region}의 주간 변동률이 검증 범위를 벗어났습니다.")
        values[region], previous[region] = current, prior
    return values, previous


def collect():
    asof_raw, detail_url = latest_release()
    detail_html = get(detail_url).text
    published = published_date(detail_html)
    appendix = appendix_text(detail_html)
    sale_text, lease_text = split_sale_lease(appendix["text"])
    sale, sale_prev = parse_appendix_table(sale_text, asof_raw)
    lease, lease_prev = parse_appendix_table(lease_text, asof_raw)
    from update_mortgage_rates import collect_bok
    rate = collect_bok()
    return {
        "source": "Korea Real Estate Board / Bank of Korea",
        "sourceMethod": "REB official PDF appendix",
        "sourceUrl": appendix["viewerUrl"], "releaseUrl": detail_url,
        "sourceDocument": {"fileKey": appendix["fileKey"], "appendixPage": appendix["page"],
                           "textSha256": appendix["textSha256"]},
        "asOf": f"{asof_raw[:4]}-{asof_raw[4:6]}-{asof_raw[6:]}", "published": published,
        "baseRate": {"value": rate["value"], "previous": rate["previous"],
                     "changedAt": rate["changed_at"], "source": rate["source_url"]},
        "regions": [{"name": name, "sale": sale[name], "salePrev": sale_prev[name],
                     "lease": lease[name], "leasePrev": lease_prev[name]} for name in REGIONS],
    }


def main():
    data = collect()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Official REB {data['asOf']}, published {data['published']}, {len(data['regions'])} regions")


if __name__ == "__main__":
    main()
