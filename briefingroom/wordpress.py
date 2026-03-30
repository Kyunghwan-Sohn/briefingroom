from __future__ import annotations

import html
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from briefingroom.config import CAT_MAP

WP_URL  = os.environ.get("WP_URL", "https://govbrief.kr")
WP_USER = os.environ.get("WP_USER", "")
WP_PASS = os.environ.get("WP_PASS", "")

MAX_RETRIES = 3


def _wp_post_with_retry(payload, label="WP"):
    for attempt in range(MAX_RETRIES):
        try:
            r = _wp_post("/wp-json/wp/v2/posts", json=payload, timeout=30)
            if r.status_code in (200, 201):
                post_id = r.json().get("id")
                post_url = r.json().get("link", "")
                print(f"    ✅ {label} #{post_id} {post_url}")
                return (post_id, post_url)  # (id, link) 튜플 반환
            if r.status_code >= 500 or r.status_code == 429:
                wait = 2 ** attempt * 5
                print(f"    [{label} 재시도] HTTP {r.status_code}, {wait}초 대기 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            print(f"    ❌ {label} 오류: {r.status_code} {r.text[:100]}")
            return False
        except (requests.ConnectionError, requests.Timeout) as e:
            wait = 2 ** attempt * 5
            print(f"    [{label} 재시도] {e}, {wait}초 대기 ({attempt+1}/{MAX_RETRIES})")
            time.sleep(wait)
        except Exception as e:
            print(f"    ❌ {label} 예외: {e}")
            return False
    print(f"    ❌ {label} 재시도 모두 실패")
    return False

_posted_titles: set = set()
_wp_cat_cache = {}
_wp_tag_cache = {}
_wp_titles_by_date = {}
_wp_session = requests.Session()


def _safe_text(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _safe_url(value) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return html.escape(url, quote=True)
    return ""


def _wp_get(path: str, **kwargs):
    return _wp_session.get(f"{WP_URL}{path}", auth=(WP_USER, WP_PASS), **kwargs)


def _wp_post(path: str, **kwargs):
    return _wp_session.post(f"{WP_URL}{path}", auth=(WP_USER, WP_PASS), **kwargs)


def _prefetch_post_titles(date_str: str) -> set[str]:
    cached = _wp_titles_by_date.get(date_str)
    if cached is not None:
        return cached

    import html as _html

    titles = set()
    after = f"{date_str}T00:00:00"
    before = f"{date_str}T23:59:59"
    try:
        for pg in range(1, 6):
            r = _wp_get(
                "/wp-json/wp/v2/posts",
                params={
                    "after": after,
                    "before": before,
                    "per_page": 100,
                    "page": pg,
                    "_fields": "id,title",
                },
                timeout=10,
            )
            r.raise_for_status()
            payload = r.json()
            if not payload:
                break
            for post in payload:
                titles.add(_html.unescape(post.get("title", {}).get("rendered", "")).strip())
            if len(payload) < 100:
                break
    except Exception as e:
        print(f"    [중복목록 조회 실패] {date_str}: {e}")
        return None
    _wp_titles_by_date[date_str] = titles
    return titles


def _get_or_create_term(cache: dict, taxonomy: str, name: str) -> int:
    if name in cache:
        return cache[name]
    try:
        r = _wp_get(f"/wp-json/wp/v2/{taxonomy}",
                    params={"search": name, "per_page": 100},
                    timeout=10)
        r.raise_for_status()
        for term in r.json():
            if term.get("name") == name:
                cache[name] = term["id"]
                return term["id"]

        r2 = _wp_post(f"/wp-json/wp/v2/{taxonomy}", json={"name": name}, timeout=10)
        r2.raise_for_status()
        term_id = r2.json().get("id", 1)
        cache[name] = term_id
        return term_id
    except Exception as e:
        print(f"    [{taxonomy} 조회/생성 실패] {name}: {e}")
        return cache.get("브리핑룸", 1 if taxonomy == "categories" else 0)

def wp_check_duplicate(title: str, date_str: str) -> bool:
    key = f"{date_str}::{title.strip()}"
    if key in _posted_titles:
        print(f"    [중복 스킵] {title[:40]}")
        return True
    try:
        titles = _prefetch_post_titles(date_str)
        if titles is None:
            return None
        if title.strip() in titles:
            print(f"    [중복 스킵] {title[:40]}")
            _posted_titles.add(key)
            return True
        return False
    except Exception as e:
        print(f"    [중복체크 실패] {e}")
        return None

def wp_get_or_create_category(name):
    return _get_or_create_term(_wp_cat_cache, "categories", name)

def wp_post(item):
    has_summary = item.get("summary") and not item["summary"].startswith("[")
    # 요약 없어도 제목+원문링크가 있으면 포스팅 허용
    if not has_summary and not item.get("title"):
        return False

    # 중복 체크
    duplicate_check = wp_check_duplicate(item["title"], item["date"])
    if duplicate_check is None:
        raise RuntimeError("WP 중복 체크 실패")
    if duplicate_check:
        return False

    summary = ""
    keywords = []
    if has_summary:
        from briefingroom.storage import extract_summary_parts
        summary, keywords, _ = extract_summary_parts(item["summary"])
    if not summary:
        summary = f'{item["source"]} 보도자료입니다. 원문 링크에서 상세 내용을 확인하세요.'

    source_text = _safe_text(item.get("source", ""))
    date_text = _safe_text(item.get("date", ""))
    summary_html = _safe_text(summary)
    source_url = _safe_url(item.get("url", ""))

    cat_name = CAT_MAP.get(item["source"], "브리핑룸")
    cat_ids  = [
        wp_get_or_create_category("브리핑룸"),
        wp_get_or_create_category(cat_name),
    ]

    file_links = ""
    for f in item.get("files", []):
        fname = Path(f).name
        if source_url:
            file_links += f'<li><a href="{source_url}" target="_blank" rel="noopener noreferrer">📎 {_safe_text(fname)}</a></li>'

    kw_html = ""
    if keywords:
        kw_html = '<div class="briefing-keywords">' + \
                  " ".join(f"<span>#{_safe_text(k)}</span>" for k in keywords if k) + "</div>"

    # 관련 뉴스 HTML
    news_html = item.get("news_html", "")

    source_link_html = (
        f'<li><a href="{source_url}" target="_blank" rel="noopener noreferrer">↗ 원문 보기</a></li>'
        if source_url else ""
    )

    content_html = f"""
<div class="briefing-post">
  <div class="briefing-meta">
    <span class="briefing-source">🏛 {source_text}</span>
    <span class="briefing-date">📅 {date_text}</span>
  </div>
  <div class="briefing-summary">
    <h3>📋 AI 요약</h3>
    <p>{summary_html}</p>
  </div>
  {kw_html}
  {news_html}
  <div class="briefing-links">
    <h4>🔗 원문 및 첨부파일</h4>
    <ul>
      {source_link_html}
      {file_links}
    </ul>
  </div>
</div>
"""

    # 태그 ID 생성/조회 (캐시 활용)
    tag_ids = []
    for kw in keywords:
        if not kw: continue
        if kw in _wp_tag_cache:
            tag_ids.append(_wp_tag_cache[kw])
            continue
        try:
            tag_id = _get_or_create_term(_wp_tag_cache, "tags", kw)
            if tag_id:
                tag_ids.append(tag_id)
        except Exception as e:
            print(f"    [태그 생성 실패] {kw}: {e}")

    payload = {
        "title":      item["title"],
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
        "tags":       tag_ids,
        "date":       f"{item['date']}T00:01:00",
    }

    result = _wp_post_with_retry(payload, label="WP")
    if result:
        _posted_titles.add(f"{item['date']}::{item['title'].strip()}")
        _wp_titles_by_date.setdefault(item["date"], set()).add(item["title"].strip())
    return result
