from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

OUT = Path('news-link-data.json')
KST = ZoneInfo('Asia/Seoul')
UA = {'User-Agent': 'Mozilla/5.0 AppleWebKit/537.36 Chrome/124 Safari/537.36'}

QUERIES = [
    ('news', 'kr', '한국 경제 증시 금리 환율 반도체 when:1d'),
    ('news', 'us', '미국 경제 연준 금리 인플레이션 증시 when:1d'),
    ('article', 'kr', '경제 분석 증시 전망 투자 전략 when:2d'),
    ('article', 'global', '글로벌 경제 시장 분석 금리 인플레이션 when:2d'),
    ('realtime', 'kr', '경제 속보 증시 속보 환율 속보 when:1d'),
    ('realtime', 'us', 'Fed inflation stocks markets when:1d'),
    ('opinion', 'kr', '경제 오피니언 칼럼 사설 증시 when:7d'),
    ('opinion', 'global', 'economy opinion markets column when:7d'),
    ('news', 'us', '(site:federalreserve.gov OR site:bls.gov OR site:bea.gov OR site:sec.gov) economy when:7d'),
    ('news', 'kr', '(site:bok.or.kr OR site:fsc.go.kr OR site:kostat.go.kr OR site:moef.go.kr) 경제 when:7d'),
]

OFFICIAL_ALIASES = {
    'federal reserve', 'federal reserve board', 'board of governors of the federal reserve system',
    'u.s. bureau of labor statistics', 'bureau of labor statistics', 'bls',
    'u.s. bureau of economic analysis', 'bureau of economic analysis', 'bea',
    'u.s. securities and exchange commission', 'securities and exchange commission', 'sec',
    '한국은행', 'bank of korea', '금융위원회', 'financial services commission',
    '금융감독원', 'financial supervisory service', '통계청', 'statistics korea',
    '기획재정부', 'ministry of economy and finance',
}

TIER_A_ALIASES = {
    'reuters', '로이터', 'bloomberg', '블룸버그', 'the wall street journal', 'wall street journal', 'wsj',
    'financial times', 'ft', 'associated press', 'ap news', 'ap', 'cnbc', 'bbc', 'nikkei asia', 'nikkei',
    '연합뉴스', '한국경제', '매일경제', '뉴스1', '연합인포맥스',
}

TIER_B_ALIASES = {
    '서울경제', '이데일리', '머니투데이', '파이낸셜뉴스', '아시아경제', '뉴시스', '조선비즈',
    '전자신문', '중앙일보', '조선일보', '동아일보', 'kbs 뉴스', 'mbc 뉴스', 'sbs 뉴스',
    '매경이코노미', '한경비즈니스',
}

BLOCKED_SOURCE_PARTS = {
    'litefinance', 'simplywall.st', 'simply wall st', 'the motley fool', 'motley fool',
}

STOPWORDS = {
    '오늘','내일','이번','관련','전망','분석','속보','단독','종합','영상','기자','뉴스','시장','증시','경제',
    '미국','한국','글로벌','국내','주요','다시','올해','내년','대해','대한','통해','따라','가운데','기대',
    'the','a','an','to','of','for','and','in','on','as','with','from','after','before','amid','says','say',
}


def feed_url(q: str) -> str:
    return 'https://news.google.com/rss/search?' + urllib.parse.urlencode(
        {'q': q, 'hl': 'ko', 'gl': 'KR', 'ceid': 'KR:ko'}
    )


def clean(s: str | None) -> str:
    if not s:
        return ''
    s = re.sub(r'<[^>]+>', ' ', html.unescape(s))
    return re.sub(r'\s+', ' ', s).strip()


def source_key(source: str) -> str:
    return re.sub(r'\s+', ' ', source.lower().strip())


def source_profile(source: str) -> dict:
    key = source_key(source)
    if any(part in key for part in BLOCKED_SOURCE_PARTS):
        return {'blocked': True, 'tier': 'X', 'score': 0, 'official': False, 'trusted': False}
    if key in OFFICIAL_ALIASES or any(alias in key for alias in OFFICIAL_ALIASES if len(alias) >= 6):
        return {'blocked': False, 'tier': 'OFFICIAL', 'score': 100, 'official': True, 'trusted': True}
    if key in TIER_A_ALIASES or any(alias in key for alias in TIER_A_ALIASES if len(alias) >= 5):
        return {'blocked': False, 'tier': 'A', 'score': 90, 'official': False, 'trusted': True}
    if key in TIER_B_ALIASES or any(alias in key for alias in TIER_B_ALIASES if len(alias) >= 5):
        return {'blocked': False, 'tier': 'B', 'score': 75, 'official': False, 'trusted': True}
    return {'blocked': False, 'tier': 'C', 'score': 45, 'official': False, 'trusted': False}


def topic_for(title: str) -> tuple[str, str]:
    t = title.lower()
    if any(k in t for k in ['연준', 'fed', 'fomc', '금리']):
        return ('미 연준', '')
    if any(k in t for k in ['코스피', '코스닥', '나스닥', '증시', '주가']):
        return ('마켓\n인사이트', 'market')
    if any(k in t for k in ['환율', '달러', '채권', '국채']):
        return ('데일리\n이코', 'daily')
    if any(k in t for k in ['반도체', '실적', '기업', '투자']):
        return ('투자\n프리뷰', 'invest')
    return ('데일리\n이코', 'daily')


def parse_feed(tab: str, region: str, q: str) -> list[dict]:
    r = requests.get(feed_url(q), headers=UA, timeout=25)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    out = []
    for item in root.findall('.//item')[:14]:
        title = clean(item.findtext('title'))
        link = clean(item.findtext('link'))
        desc = clean(item.findtext('description'))
        pub = item.findtext('pubDate')
        src = item.find('source')
        source = clean(src.text if src is not None else '')
        if source and title.endswith(' - ' + source):
            title = title[:-(len(source) + 3)]
        profile = source_profile(source)
        if profile['blocked']:
            continue
        try:
            dt = parsedate_to_datetime(pub).astimezone(KST)
        except Exception:
            dt = datetime.now(KST)
        topic, cls = topic_for(title)
        if len(desc) > 115:
            desc = desc[:112].rstrip() + '…'
        out.append({
            'tab': tab,
            'region': region,
            'topic': topic,
            'topic_class': cls,
            'title': title,
            'snippet': desc or source,
            'url': link,
            'published_at': dt.isoformat(),
            'source': source,
            'source_tier': profile['tier'],
            'source_score': profile['score'],
            'official_source': profile['official'],
            'trusted_source': profile['trusted'],
            'cross_confirmed': False,
            'cross_count': 1,
            'cross_sources': [source] if source else [],
        })
    return out


def title_tokens(title: str) -> set[str]:
    s = re.sub(r'\[[^\]]{0,30}\]|【[^】]{0,30}】|\([^)]{0,20}\)', ' ', title.lower())
    s = re.sub(r'[^0-9a-zA-Z가-힣%.$+-]+', ' ', s)
    toks = set()
    for tok in s.split():
        tok = tok.strip('._-+').lower()
        if len(tok) < 2 or tok in STOPWORDS:
            continue
        if re.fullmatch(r'\d{1,2}(월|일)?', tok):
            continue
        toks.add(tok)
    return toks


def same_issue(a: dict, b: dict) -> bool:
    if a.get('source') == b.get('source'):
        return False
    if not (a.get('trusted_source') and b.get('trusted_source')):
        return False
    try:
        ta = datetime.fromisoformat(a['published_at'])
        tb = datetime.fromisoformat(b['published_at'])
        if abs((ta - tb).total_seconds()) > 18 * 3600:
            return False
    except Exception:
        pass
    A, B = title_tokens(a['title']), title_tokens(b['title'])
    if not A or not B:
        return False
    inter = A & B
    union = A | B
    jaccard = len(inter) / max(1, len(union))
    containment = len(inter) / max(1, min(len(A), len(B)))
    return (len(inter) >= 3 and jaccard >= 0.38) or (len(inter) >= 4 and containment >= 0.62)


def add_cross_confirmation(items: list[dict]) -> None:
    n = len(items)
    for i in range(n):
        if not items[i].get('trusted_source'):
            continue
        matches = {items[i].get('source', '')}
        for j in range(n):
            if i == j:
                continue
            if same_issue(items[i], items[j]) and items[j].get('source'):
                matches.add(items[j]['source'])
        if len(matches) >= 2:
            items[i]['cross_confirmed'] = True
            items[i]['cross_count'] = len(matches)
            items[i]['cross_sources'] = sorted(matches)[:5]


def ranking_score(x: dict) -> float:
    score = float(x.get('source_score') or 0)
    if x.get('official_source'):
        score += 35
    if x.get('cross_confirmed'):
        score += 28 + min(12, 4 * (int(x.get('cross_count') or 2) - 2))
    return score


def main() -> None:
    now = datetime.now(KST)
    all_items: list[dict] = []
    errors = []
    try:
        for tab, region, q in QUERIES:
            try:
                all_items.extend(parse_feed(tab, region, q))
                time.sleep(.25)
            except Exception as e:
                errors.append(str(e))

        seen = set()
        items = []
        for x in sorted(all_items, key=lambda x: x['published_at'], reverse=True):
            key = re.sub(r'\W+', '', x['title'].lower())[:100]
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(x)

        if not items:
            raise RuntimeError('; '.join(errors) or 'no RSS items')

        add_cross_confirmation(items)
        for x in items:
            x['ranking_score'] = ranking_score(x)

        items.sort(key=lambda x: (x['ranking_score'], x['published_at']), reverse=True)
        counts = {
            'official': sum(1 for x in items if x.get('official_source')),
            'tier_a': sum(1 for x in items if x.get('source_tier') == 'A'),
            'tier_b': sum(1 for x in items if x.get('source_tier') == 'B'),
            'cross_confirmed': sum(1 for x in items if x.get('cross_confirmed')),
            'blocked_policy': sorted(BLOCKED_SOURCE_PARTS),
        }
        data = {
            'source': 'Google News RSS + source trust grading',
            'generated_at': now.isoformat(),
            'stale': False,
            'trust_policy_version': 2,
            'quality': counts,
            'items': items[:100],
        }
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        if OUT.exists():
            old = json.loads(OUT.read_text(encoding='utf-8'))
            old['stale'] = True
            old['last_error'] = str(exc)
            old['last_attempt_at'] = now.isoformat()
            OUT.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding='utf-8')
        else:
            raise


if __name__ == '__main__':
    main()
