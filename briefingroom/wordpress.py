from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import requests

from briefingroom.config import CAT_MAP

WP_URL  = "https://hotclipfolio.com"
WP_USER = "hotclipfolio"
WP_PASS = "qSUw w4xA ELSm w6z9 6zIU U8G8"

_posted_titles: set = set()
_wp_cat_cache = {}

def wp_check_duplicate(title: str, date_str: str) -> bool:
    key = f"{date_str}::{title.strip()}"
    if key in _posted_titles:
        print(f"    [중복 스킵] {title[:40]}")
        return True
    try:
        import html as _html
        after  = f"{date_str}T00:00:00"
        before = f"{date_str}T23:59:59"
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"after": after, "before": before,
                    "per_page": 100, "_fields": "id,title"},
            auth=(WP_USER, WP_PASS), timeout=10,
        )
        if r.status_code != 200: return False
        for p in r.json():
            existing = _html.unescape(
                p.get("title", {}).get("rendered", "")).strip()
            if existing == title.strip():
                print(f"    [중복 스킵] #{p['id']} {title[:40]}")
                _posted_titles.add(key)
                return True
        return False
    except:
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
    if not item.get("summary") or item["summary"].startswith("["):
        return False

    # 중복 체크
    if wp_check_duplicate(item["title"], item["date"]):
        return False

    summary = ""
    keywords = []
    for line in item["summary"].split("\n"):
        if line.startswith("요약:"):
            summary = line.replace("요약:", "").strip()
        elif line.startswith("키워드:"):
            keywords = [k.strip() for k in line.replace("키워드:", "").split(",")]

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

    # 태그 ID 생성/조회
    tag_ids = []
    for kw in keywords:
        if not kw: continue
        try:
            r_tag = requests.get(f"{WP_URL}/wp-json/wp/v2/tags",
                                 params={"search": kw, "per_page": 3},
                                 auth=(WP_USER, WP_PASS), timeout=10)
            found = [t for t in r_tag.json() if t["name"] == kw]
            if found:
                tag_ids.append(found[0]["id"])
            else:
                r_new = requests.post(f"{WP_URL}/wp-json/wp/v2/tags",
                                      json={"name": kw},
                                      auth=(WP_USER, WP_PASS), timeout=10)
                if r_new.status_code in (200, 201):
                    tag_ids.append(r_new.json().get("id"))
        except:
            pass

    payload = {
        "title":      item["title"],
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
        "tags":       tag_ids,
        "date":       f"{item['date']}T09:00:00",
    }

    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
                          json=payload, auth=(WP_USER, WP_PASS), timeout=30)
        if r.status_code in (200, 201):
            post_id  = r.json().get("id")
            post_url = r.json().get("link")
            print(f"    ✅ WP #{post_id} {post_url}")
            return True
        else:
            print(f"    ❌ WP 오류: {r.status_code} {r.text[:100]}")
            return False
    except Exception as e:
        print(f"    ❌ WP 예외: {e}")
        return False

def wp_post_summary(all_items, target, is_weekly=False):
    """일별/주간 종합 요약 포스팅"""
    if not all_items:
        print("  요약 포스팅: 수집 건수 없음 스킵")
        return False

    from datetime import timedelta

    # 제목 설정
    if is_weekly:
        # 주차 계산
        week_num = (target.day - 1) // 7 + 1
        post_title = f"{target.year}년 {target.month}월 {week_num}주차 주간 보도자료"
        date_range = f"{(target - timedelta(days=4)).strftime('%Y.%m.%d')} ~ {target.strftime('%Y.%m.%d')}"
        period_label = f"주간 ({date_range})"
    else:
        post_title = f"{target.year}년 {target.month}월 {target.day}일 보도자료"
        period_label = target.strftime('%Y.%m.%d')

    # 중복 체크
    if wp_check_duplicate(post_title, target.isoformat()):
        return False

    # 부처별 그룹핑
    from collections import defaultdict
    by_source = defaultdict(list)
    for item in all_items:
        if item.get('summary') and not item['summary'].startswith('['):
            by_source[item['source']].append(item)

    if not by_source:
        print("  요약 포스팅: 요약된 항목 없음 스킵")
        return False

    # 분야별 색상
    CAT_COLORS = {
        '금융경제': '#2f54eb', '사회복지': '#16a34a',
        '산업기술': '#d97706', '외교안보': '#dc2626', '행정법제': '#7c3aed'
    }

    # HTML 생성
    rows = ""
    for source, items in sorted(by_source.items()):
        cat = CAT_MAP.get(source, '행정법제')
        color = CAT_COLORS.get(cat, '#2f54eb')
        for item in items:
            summary_line = ""
            for line in item["summary"].split("\n"):
                if line.startswith("요약:"):
                    summary_line = line.replace("요약:", "").strip()
                    break
            if not summary_line:
                continue
            rows += f"""
<tr>
  <td style="padding:10px 14px;border-bottom:1px solid #e0ddd7;white-space:nowrap;vertical-align:top">
    <span style="background:{color}18;color:{color};font-size:11px;padding:2px 8px;border-radius:4px;font-family:monospace;font-weight:600">{source}</span>
  </td>
  <td style="padding:10px 14px;border-bottom:1px solid #e0ddd7;font-size:13px;line-height:1.6;color:#4a4844">
    <a href="{item['url']}" style="color:#1c1b18;text-decoration:none;font-weight:500">{item['title']}</a><br>
    <span style="color:#96938c;font-size:12px">{summary_line[:120]}{'...' if len(summary_line)>120 else ''}</span>
  </td>
</tr>"""

    total = sum(len(v) for v in by_source.values())
    content_html = f"""
<div class="briefing-post" style="font-family:'Pretendard',sans-serif">
  <div style="background:#1c1b18;padding:20px 24px;border-radius:12px 12px 0 0">
    <div style="font-family:Georgia,serif;font-size:22px;font-weight:700;color:#fff;letter-spacing:-0.5px">{post_title}</div>
    <div style="margin-top:8px;display:flex;gap:12px;align-items:center">
      <span style="background:#2f54eb;color:#fff;font-size:11px;padding:3px 12px;border-radius:20px;font-family:monospace">총 {total}건</span>
      <span style="color:rgba(255,255,255,0.5);font-size:11px;font-family:monospace">{period_label} · {len(by_source)}개 부처</span>
    </div>
  </div>
  <div style="background:#f5f4f0;padding:0">
    <table style="width:100%;border-collapse:collapse;background:#fff">
      <thead>
        <tr style="background:#f5f4f0">
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#96938c;font-family:monospace;font-weight:500;border-bottom:2px solid #e0ddd7;white-space:nowrap">부처</th>
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#96938c;font-family:monospace;font-weight:500;border-bottom:2px solid #e0ddd7">제목 / 요약</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""

    # 카테고리 설정
    cat_ids = [wp_get_or_create_category("브리핑룸")]
    if is_weekly:
        cat_ids.append(wp_get_or_create_category("주간브리핑"))
    else:
        cat_ids.append(wp_get_or_create_category("일별브리핑"))

    payload = {
        "title":      post_title,
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
        "date":       f"{target.isoformat()}T08:00:00",
    }
    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
                          json=payload, auth=(WP_USER, WP_PASS), timeout=30)
        if r.status_code in (200, 201):
            post_id  = r.json().get("id")
            post_url = r.json().get("link")
            print(f"    ✅ 요약 포스팅 #{post_id} {post_url}")
            return True
        else:
            print(f"    ❌ 요약 포스팅 오류: {r.status_code} {r.text[:100]}")
            return False
    except Exception as e:
        print(f"    ❌ 요약 포스팅 예외: {e}")
        return False
