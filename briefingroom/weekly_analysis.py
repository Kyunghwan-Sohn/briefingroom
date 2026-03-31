from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from datetime import date, timedelta

from briefingroom.config import CAT_MAP, DATA_DIR
CAT_ORDER = [
    ("금융경제", "💰"),
    ("사회복지", "🏥"),
    ("산업기술", "⚙️"),
    ("외교안보", "🌏"),
    ("행정법제", "📜"),
]


def get_week_range(target: date) -> tuple[date, date]:
    """target 기준 직전 월~토 날짜 범위"""
    end = target - timedelta(days=1)
    start = end - timedelta(days=6)
    return start, end


def _load_items_from_json(start: date, end: date) -> list[dict]:
    items = []
    current = start
    while current <= end:
        json_path = DATA_DIR / f"{current.isoformat()}.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                for item in data.get("items", []):
                    keywords = item.get("keywords", "")
                    if isinstance(keywords, list):
                        keywords = ", ".join(keywords)
                    items.append({
                        "slug": item.get("slug", ""),
                        "source": item.get("source", ""),
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "date": item.get("date", current.isoformat()),
                        "category": item.get("category", "") or CAT_MAP.get(item.get("source", ""), "행정법제"),
                        "summary": item.get("summary", ""),
                        "keywords": keywords,
                    })
            except Exception as e:
                print(f"  [JSON] {json_path.name} 로드 실패: {e}")
        current += timedelta(days=1)
    return items


def analyze_weekly(target: date) -> dict:
    """data/ JSON 파일에서 7일 + 전주 7일 집계"""
    start, end = get_week_range(target)
    prev_start = start - timedelta(days=7)
    prev_end = start - timedelta(days=1)

    rows = _load_items_from_json(start, end)
    prev_rows = _load_items_from_json(prev_start, prev_end)

    total = len(rows)
    by_cat = Counter()
    by_source = Counter()
    keywords = Counter()
    items_by_cat = defaultdict(list)

    for row in rows:
        category = row["category"] or CAT_MAP.get(row["source"], "행정법제")
        by_cat[category] += 1
        by_source[row["source"]] += 1
        items_by_cat[category].append(row)
        if row["keywords"]:
            for keyword in row["keywords"].split(","):
                keyword = keyword.strip()
                if keyword and len(keyword) > 1:
                    keywords[keyword] += 1

    prev_total = len(prev_rows)
    prev_by_source = Counter(row["source"] for row in prev_rows)
    prev_keywords = Counter()
    for row in prev_rows:
        if row.get("keywords"):
            for keyword in row["keywords"].split(","):
                keyword = keyword.strip()
                if keyword and len(keyword) > 1:
                    prev_keywords[keyword] += 1

    source_delta = {}
    for source in set(by_source.keys()) | set(prev_by_source.keys()):
        source_delta[source] = by_source.get(source, 0) - prev_by_source.get(source, 0)

    kw_delta = {}
    for keyword, count in keywords.most_common(30):
        prev_count = prev_keywords.get(keyword, 0)
        change_pct = ((count - prev_count) / prev_count * 100) if prev_count > 0 else 999
        kw_delta[keyword] = {"count": count, "prev": prev_count, "change_pct": change_pct}

    return {
        "start": start,
        "end": end,
        "total": total,
        "prev_total": prev_total,
        "by_cat": dict(by_cat),
        "by_source": by_source,
        "prev_by_source": prev_by_source,
        "source_delta": source_delta,
        "keywords": keywords,
        "kw_delta": kw_delta,
        "items_by_cat": items_by_cat,
        "sources_count": len(by_source),
    }


def select_weekly_top(analysis: dict) -> dict:
    """분야별 TOP 1 — Google News RSS 기사 수 기반"""
    from briefingroom.news import search_related_news

    selected = {}
    for cat, _ in CAT_ORDER:
        items = analysis["items_by_cat"].get(cat, [])
        if not items:
            continue

        candidates = [item for item in items if item.get("summary") and not item["summary"].startswith("[")]
        if not candidates:
            candidates = items[:5]

        by_source = defaultdict(list)
        for item in candidates:
            by_source[item["source"]].append(item)

        source_tops = sorted(
            [(source, source_items[0], len(source_items)) for source, source_items in by_source.items()],
            key=lambda row: -row[2],
        )

        best = None
        best_news_count = -1
        for source, item, count in source_tops[:5]:
            articles = search_related_news(item["title"], source, max_results=100)
            news_count = len(articles)
            print(f"    [{cat}] {source}: \"{item['title'][:30]}...\" -> 뉴스 {news_count}건")
            if news_count > best_news_count:
                best_news_count = news_count
                best = (source, item, count, news_count, articles[:2])
            time.sleep(0.3)

        if best:
            selected[cat] = best

    return selected
