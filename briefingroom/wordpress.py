from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from briefingroom.config import CAT_MAP

WP_URL  = os.environ.get("WP_URL", "https://hotclipfolio.com")
WP_USER = os.environ.get("WP_USER", "")
WP_PASS = os.environ.get("WP_PASS", "")

MAX_RETRIES = 3


def _wp_post_with_retry(payload, label="WP"):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
                              json=payload, auth=(WP_USER, WP_PASS), timeout=30)
            if r.status_code in (200, 201):
                post_id = r.json().get("id")
                post_url = r.json().get("link")
                print(f"    ✅ {label} #{post_id} {post_url}")
                return True
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

def wp_check_duplicate(title: str, date_str: str) -> bool:
    key = f"{date_str}::{title.strip()}"
    if key in _posted_titles:
        print(f"    [중복 스킵] {title[:40]}")
        return True
    try:
        import html as _html
        after  = f"{date_str}T00:00:00"
        before = f"{date_str}T23:59:59"
        # 페이지네이션으로 100건 이상 검색
        for pg in range(1, 6):
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={"after": after, "before": before,
                        "per_page": 100, "page": pg, "_fields": "id,title"},
                auth=(WP_USER, WP_PASS), timeout=10,
            )
            if r.status_code != 200 or not r.json():
                break
            for p in r.json():
                existing = _html.unescape(
                    p.get("title", {}).get("rendered", "")).strip()
                if existing == title.strip():
                    print(f"    [중복 스킵] #{p['id']} {title[:40]}")
                    _posted_titles.add(key)
                    return True
            if len(r.json()) < 100:
                break
        return False
    except Exception as e:
        print(f"    [중복체크 실패] {e}")
        return False

def wp_get_or_create_category(name):
    if name in _wp_cat_cache:
        return _wp_cat_cache[name]
    auth = (WP_USER, WP_PASS)
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories",
                     params={"search": name, "per_page": 5}, auth=auth, timeout=10)
    for cat in r.json():
        if cat["name"] == name:
            _wp_cat_cache[name] = cat["id"]
            return cat["id"]
    r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/categories",
                       json={"name": name}, auth=auth, timeout=10)
    cat_id = r2.json().get("id", 1)
    _wp_cat_cache[name] = cat_id
    return cat_id

def wp_post(item):
    has_summary = item.get("summary") and not item["summary"].startswith("[")
    # 요약 없어도 제목+원문링크가 있으면 포스팅 허용
    if not has_summary and not item.get("title"):
        return False

    # 중복 체크
    if wp_check_duplicate(item["title"], item["date"]):
        return False

    summary = ""
    keywords = []
    if has_summary:
        for line in item["summary"].split("\n"):
            if line.startswith("요약:"):
                summary = line.replace("요약:", "").strip()
            elif line.startswith("키워드:"):
                keywords = [k.strip() for k in line.replace("키워드:", "").split(",")]
    if not summary:
        summary = f'{item["source"]} 보도자료입니다. 원문 링크에서 상세 내용을 확인하세요.'

    cat_name = CAT_MAP.get(item["source"], "브리핑룸")
    cat_ids  = [
        wp_get_or_create_category("브리핑룸"),
        wp_get_or_create_category(cat_name),
    ]

    file_links = ""
    for f in item.get("files", []):
        fname = Path(f).name
        file_links += f'<li><a href="{item["url"]}" target="_blank">📎 {fname}</a></li>'

    kw_html = ""
    if keywords:
        kw_html = '<div class="briefing-keywords">' + \
                  " ".join(f"<span>#{k}</span>" for k in keywords) + "</div>"

    content_html = f"""
<div class="briefing-post">
  <div class="briefing-meta">
    <span class="briefing-source">🏛 {item["source"]}</span>
    <span class="briefing-date">📅 {item["date"]}</span>
  </div>
  <div class="briefing-summary">
    <h3>📋 AI 요약</h3>
    <p>{summary}</p>
  </div>
  {kw_html}
  <div class="briefing-links">
    <h4>🔗 원문 및 첨부파일</h4>
    <ul>
      <li><a href="{item["url"]}" target="_blank">↗ 원문 보기</a></li>
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
            r_tag = requests.get(f"{WP_URL}/wp-json/wp/v2/tags",
                                 params={"search": kw, "per_page": 3},
                                 auth=(WP_USER, WP_PASS), timeout=10)
            found = [t for t in r_tag.json() if t["name"] == kw]
            if found:
                _wp_tag_cache[kw] = found[0]["id"]
                tag_ids.append(found[0]["id"])
            else:
                r_new = requests.post(f"{WP_URL}/wp-json/wp/v2/tags",
                                      json={"name": kw},
                                      auth=(WP_USER, WP_PASS), timeout=10)
                if r_new.status_code in (200, 201):
                    tag_id = r_new.json().get("id")
                    _wp_tag_cache[kw] = tag_id
                    tag_ids.append(tag_id)
        except Exception as e:
            print(f"    [태그 생성 실패] {kw}: {e}")

    payload = {
        "title":      item["title"],
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
        "tags":       tag_ids,
        "date":       f"{item['date']}T09:00:00",
    }

    result = _wp_post_with_retry(payload, label="WP")
    if result:
        _posted_titles.add(f"{item['date']}::{item['title'].strip()}")
    return result

