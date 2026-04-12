"""브리핑룸 키워드 집계 배치

data/YYYY-MM-DD.json 파일들에서 각 보도자료의 keywords 필드를 집계해
/keywords/ 페이지가 소비할 정적 JSON을 생성한다.

출력:
    data/keywords-7d.json
    data/keywords-30d.json
    data/keywords-90d.json

실행: python -m briefingroom.keywords_agg
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from briefingroom.config import DATA_DIR
from briefingroom.home_gen import CAT_LABELS, SHORT_SOURCE

PERIODS = (7, 30, 90)
TOP_N = 100
TOP_PER_CATEGORY = 30
MAX_ARTICLES_PER_KW = 10
MIN_COUNT = 2  # 최소 언급 횟수 (노이즈 컷오프)

DATE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")

# 부처·기관명은 source 필드에 이미 있으므로 키워드로는 노이즈
_MINISTRY_STOP = {
    "기획재정부", "기재부", "재정경제부", "금융위원회", "금융위", "금융감독원", "금감원",
    "과학기술정보통신부", "과기부", "산업통상자원부", "산업부",
    "중소벤처기업부", "중기부", "국토교통부", "국토부", "해양수산부", "해수부",
    "농림축산식품부", "농식품부", "농촌진흥청", "보건복지부", "복지부",
    "고용노동부", "고용부", "환경부", "외교부", "교육부", "법무부", "국방부", "통일부",
    "행정안전부", "행안부", "여성가족부", "여가부", "성평등가족부",
    "문화체육관광부", "문체부", "식품의약품안전처", "식약처",
    "기후에너지환경부", "기후환경부", "한국은행",
    "조달청", "산림청", "관세청", "국세청", "경찰청", "소방청", "병무청", "기상청",
    "국가유산청", "방위사업청", "국가보훈부", "지식재산처", "지식재산청", "특허청",
    "공정거래위원회", "공정위", "개인정보보호위원회", "개인정보위",
    "국민권익위원회", "국민권익위", "국민통합위원회", "국민통합위",
    "국가정보원", "국정원", "감사원", "대통령실", "국무총리실", "국무조정실",
    "통계청", "행복청", "새만금청", "원자력안전위원회", "원안위",
}

# 동의어 정규화 (집계 키 → 표시명)
_SYNONYM_CANONICAL = {
    "ai": "인공지능",
    "인공지능": "인공지능",
}

# 패턴 기반 노이즈 (연도·날짜·의례적 이벤트 단어)
_NOISE_PATTERNS = [
    re.compile(r"^\d{4}\s*년?$"),           # "2026", "2026년"
    re.compile(r"^\d{4}\s*년\s*\d+\s*월$"),  # "2026년 4월"
    re.compile(r"^\d+\s*월(\s*\d+\s*일)?$"),
    re.compile(r"^\d+\s*차$"),
]
_EVENT_STOP = {
    "간담회", "업무협약", "현장 점검", "현장점검", "임명", "공휴일 지정",
    "기자회견", "기념식", "행사", "축사", "성명", "축전", "업무보고",
    "브리핑", "설명회", "세미나", "포럼", "협약", "간담", "체결식",
}
_STOP_KEYS_EVENT = {re.sub(r"\s+", "", s).lower() for s in _EVENT_STOP}


def _is_noise(display: str, key: str) -> bool:
    if key in _STOP_KEYS_EVENT:
        return True
    for pat in _NOISE_PATTERNS:
        if pat.match(display):
            return True
    return False

# SHORT_SOURCE key/value 모두 추가 흡수
STOPWORDS: set[str] = (
    _MINISTRY_STOP
    | set(SHORT_SOURCE.keys())
    | set(SHORT_SOURCE.values())
)
_STOP_KEYS: set[str] = {re.sub(r"\s+", "", s).lower() for s in STOPWORDS}


def _short_source(source: str) -> str:
    return SHORT_SOURCE.get(source, source)


def _iter_date_files(since: date, until: date) -> Iterable[tuple[date, Path]]:
    for p in sorted(DATA_DIR.glob("*.json")):
        m = DATE_FILE_RE.match(p.name)
        if not m:
            continue
        file_date = date.fromisoformat(m.group(1))
        if since <= file_date <= until:
            yield file_date, p


def _load_items(since: date, until: date) -> list[dict]:
    items: list[dict] = []
    for file_date, p in _iter_date_files(since, until):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [skip] {p.name}: {e}")
            continue
        for it in payload.get("items", []) or []:
            if not it.get("date"):
                it["date"] = file_date.isoformat()
            items.append(it)
    return items


def _normalize_kw(kw: str) -> str:
    """표시용: 공백 정리·양쪽 특수문자 제거."""
    kw = (kw or "").strip()
    kw = re.sub(r"\s+", " ", kw)
    kw = kw.strip("·•,.;:·\"'`")
    return kw


def _dedupe_key(kw: str) -> str:
    """집계용 키: 공백 제거 + 소문자.

    '중동 전쟁' == '중동전쟁', 'AI' == 'ai' 처럼 변형을 병합."""
    key = re.sub(r"\s+", "", kw).lower()
    return _SYNONYM_CANONICAL.get(key, key)


def _extract_keywords(item: dict) -> list[tuple[str, str]]:
    """리턴: [(dedupe_key, display), ...]"""
    raw = item.get("keywords") or []
    if isinstance(raw, str):
        raw = [k for k in raw.split(",")]
    out: list[tuple[str, str]] = []
    for k in raw:
        display = _normalize_kw(k)
        if not display or display in STOPWORDS or len(display) > 40:
            continue
        key = _dedupe_key(display)
        if not key or key in _STOP_KEYS:
            continue
        if _is_noise(display, key):
            continue
        out.append((key, display))
    return out


def aggregate(period_days: int, today: date | None = None) -> dict:
    today = today or date.today()
    since = today - timedelta(days=period_days - 1)
    items = _load_items(since, today)

    # key(dedupe) 기준 집계, display는 해당 key 중 가장 빈번한 원형 사용
    kw_count: Counter[str] = Counter()
    kw_cat_count: dict[str, Counter[str]] = defaultdict(Counter)
    kw_sources: dict[str, Counter[str]] = defaultdict(Counter)
    kw_articles: dict[str, list[dict]] = defaultdict(list)
    kw_display_count: dict[str, Counter[str]] = defaultdict(Counter)

    for it in items:
        pairs = _extract_keywords(it)
        if not pairs:
            continue
        raw_cat = it.get("category", "") or ""
        cat_label = CAT_LABELS.get(raw_cat, raw_cat or "기타")
        src_short = _short_source(it.get("source", "") or "")
        ref = {
            "date": it.get("date", ""),
            "slug": it.get("slug", ""),
            "source": src_short,
            "title": it.get("title", ""),
        }
        for key, display in pairs:
            kw_count[key] += 1
            kw_cat_count[key][cat_label] += 1
            kw_sources[key][src_short] += 1
            kw_display_count[key][display] += 1
            if len(kw_articles[key]) < MAX_ARTICLES_PER_KW:
                kw_articles[key].append(ref)

    kw_category: dict[str, str] = {
        key: (cats.most_common(1)[0][0] if cats else "기타")
        for key, cats in kw_cat_count.items()
    }
    kw_display: dict[str, str] = {
        key: (disps.most_common(1)[0][0] if disps else key)
        for key, disps in kw_display_count.items()
    }

    filtered = [(key, cnt) for key, cnt in kw_count.most_common() if cnt >= MIN_COUNT]

    top_list = [
        {
            "keyword": kw_display.get(key, key),
            "count": cnt,
            "category": kw_category.get(key, "기타"),
            "top_sources": [s for s, _ in kw_sources[key].most_common(5)],
            "articles": kw_articles[key],
        }
        for key, cnt in filtered[:TOP_N]
    ]

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for key, cnt in filtered:
        cat = kw_category.get(key, "기타")
        if len(by_cat[cat]) < TOP_PER_CATEGORY:
            by_cat[cat].append({"keyword": kw_display.get(key, key), "count": cnt})

    cat_totals = {cat: sum(x["count"] for x in lst) for cat, lst in by_cat.items()}

    return {
        "period": f"{period_days}d",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "start_date": since.isoformat(),
        "end_date": today.isoformat(),
        "article_count": len(items),
        "unique_keywords": len(kw_count),
        "total_mentions": sum(kw_count.values()),
        "category_totals": cat_totals,
        "top": top_list,
        "by_category": {cat: lst for cat, lst in by_cat.items()},
    }


def run() -> dict[int, Path]:
    print(f"[keywords_agg] data: {DATA_DIR}")
    out_paths: dict[int, Path] = {}
    for days in PERIODS:
        print(f"\n[{days}일]")
        result = aggregate(days)
        out_path = DATA_DIR / f"keywords-{days}d.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        out_paths[days] = out_path
        print(
            f"  기사 {result['article_count']}건 / "
            f"키워드 {result['unique_keywords']}개 / "
            f"총언급 {result['total_mentions']}회"
        )
        top5 = [x["keyword"] for x in result["top"][:5]]
        if top5:
            print(f"  Top 5: {top5}")
        print(f"  → {out_path.name}")
    return out_paths


if __name__ == "__main__":
    run()
