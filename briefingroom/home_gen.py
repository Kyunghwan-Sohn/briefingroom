"""홈 페이지(index.html) 동적 생성

latest.json에서 데이터를 읽어 캐러셀, 부처별 브리핑 등을 자동 생성합니다.

실행: python -m briefingroom.home_gen
"""
from __future__ import annotations

import html as h
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import sqlite3

from briefingroom.config import BASE_DIR, DATA_DIR

INDEX_PATH = BASE_DIR / "index.html"
POLICY_INDEX_PATH = BASE_DIR / "policy" / "index.html"
FINLAW_DB = BASE_DIR / "finance_law.db"

# 카테고리 한글명
CAT_LABELS = {
    "금융경제": "금융·경제",
    "산업기술": "산업·기술",
    "사회복지": "사회·복지",
    "외교안보": "외교·안보",
    "행정법제": "행정·법제",
}

IMPACT_RANK = {"상": 3, "중": 2, "하": 1}

# 부처 약칭 매핑
SHORT_SOURCE = {
    "과학기술정보통신부": "과기부",
    "농림축산식품부": "농식품부",
    "고용노동부": "고용부",
    "산업통상자원부": "산업부",
    "산업통상부": "산업부",
    "행정안전부": "행안부",
    "보건복지부": "복지부",
    "국토교통부": "국토부",
    "해양수산부": "해수부",
    "환경부": "환경부",
    "외교부": "외교부",
    "교육부": "교육부",
    "금융위원회": "금융위",
    "금융감독원": "금감원",
    "기획재정부": "기재부",
    "기획예산처": "기재부",
    "법무부": "법무부",
    "국방부": "국방부",
    "통일부": "통일부",
    "여성가족부": "여가부",
    "성평등가족부": "여가부",
    "식품의약품안전처": "식약처",
    "조달청": "조달청",
    "산림청": "산림청",
    "관세청": "관세청",
    "경찰청": "경찰청",
    "소방청": "소방청",
    "기상청": "기상청",
    "특허청": "특허청",
    "통계청": "통계청",
    "문화체육관광부": "문체부",
    "중소벤처기업부": "중기부",
    "질병관리청": "질병청",
}

# CSS (현재 index.html에서 추출)
def _read_current_css() -> str:
    if INDEX_PATH.exists():
        content = INDEX_PATH.read_text(encoding="utf-8")
        import re
        m = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
        if m:
            return m.group(1)
    return ""


def _build_policy_carousel(items: list[dict], target_date: str) -> str:
    """정책 요약 캐러셀 생성 (종합 + 카테고리별)"""
    date_display = target_date.replace("-", ".")

    # 카테고리별 분류
    by_cat = defaultdict(list)
    for it in items:
        by_cat[it.get("category", "행정법제")].append(it)

    # 영향도 상 건수
    high_count = sum(1 for it in items if it.get("impact") == "상")

    # 슬라이드 1: 종합
    top_cats = sorted(by_cat.items(), key=lambda x: -len(x[1]))[:3]
    top_keywords = []
    for it in items[:20]:
        for kw in (it.get("keywords") or [])[:2]:
            if kw and f"#{kw}" not in top_keywords and len(top_keywords) < 3:
                top_keywords.append(f"#{kw}")

    summary_title = " · ".join(CAT_LABELS.get(c, c) for c, _ in top_cats[:3])
    summary_body = f"오늘 51개 부처에서 {len(items)}건이 발표되었습니다."
    if top_cats:
        parts = []
        for cat, cat_items in top_cats[:3]:
            if cat_items:
                parts.append(f"{CAT_LABELS.get(cat, cat)} {len(cat_items)}건")
        summary_body += " " + ", ".join(parts) + "."

    kw_html = "".join(f"<span>{h.escape(k)}</span>" for k in top_keywords)
    slides = [f"""<div class="carousel-card">
        <div class="sum-label">종합 1/{1 + len(top_cats)}</div>
        <div class="sum-title">{h.escape(summary_title)}</div>
        <div class="sum-kw">{kw_html}</div>
        <div class="sum-body">{h.escape(summary_body)}</div>
        <div class="sum-foot"><a href="/articles/">상세 브리핑 →</a><span>영향도 상 {high_count}건</span></div>
      </div>"""]

    # 슬라이드 2~: 카테고리별
    for idx, (cat, cat_items) in enumerate(top_cats, 2):
        cat_label = CAT_LABELS.get(cat, cat)
        # 카테고리 내 상위 항목의 요약에서 핵심 추출
        titles = []
        cat_kws = []
        for ci in cat_items[:3]:
            summary = ci.get("summary", "")
            if summary:
                titles.append(summary[:30])
            for kw in (ci.get("keywords") or [])[:2]:
                if kw and f"#{kw}" not in cat_kws and len(cat_kws) < 3:
                    cat_kws.append(f"#{kw}")

        slide_title = " · ".join(titles[:3]) if titles else f"{cat_label} 주요 정책"
        slide_body = f"{cat_label} 분야에서 {len(cat_items)}건이 발표되었습니다."
        if cat_items and cat_items[0].get("summary"):
            slide_body = cat_items[0]["summary"][:150]

        cat_kw_html = "".join(f"<span>{h.escape(k)}</span>" for k in cat_kws)

        # 부처 목록
        sources = set(ci.get("source", "") for ci in cat_items[:5])
        source_text = ", ".join(list(sources)[:3])

        slides.append(f"""<div class="carousel-card">
        <div class="sum-label">{h.escape(cat_label)} {idx}/{1 + len(top_cats)}</div>
        <div class="sum-title">{h.escape(slide_title[:60])}</div>
        <div class="sum-kw">{cat_kw_html}</div>
        <div class="sum-body">{h.escape(slide_body)}</div>
        <div class="sum-foot"><a href="/articles/">{h.escape(cat_label)} {len(cat_items)}건 →</a><span>{h.escape(source_text)}</span></div>
      </div>""")

    slide_count = len(slides)
    dots = "".join(f'<span class="carousel-dot{" on" if i == 0 else ""}"></span>' for i in range(slide_count))

    return f"""<div class="sec-hdr">오늘의 정책 요약 <span style="font-family:var(--mono);font-size:18px;font-weight:700;color:var(--t);margin-left:8px">{date_display}</span><a class="sec-more" href="/articles/">전체 {len(items)}건 →</a></div>
  <div class="carousel" id="c1">
    <div class="carousel-track" id="c1-track">
      {"".join(slides)}
    </div>
    <div class="carousel-dots" id="c1-dots">{dots}</div>
  </div>""", slide_count


def _build_twin_carousel(policy_items: list[dict], date_display: str) -> str:
    """홈 2분할 캐러셀: 왼쪽 정책AI + 오른쪽 법령AI"""

    # 왼쪽: 정책 AI (영향도 상 우선 3건)
    top_policy = sorted(
        policy_items,
        key=lambda x: (-IMPACT_RANK.get(x.get("impact", "중"), 2), x.get("title", "")),
    )[:3]

    policy_slides = []
    for it in top_policy:
        cat = CAT_LABELS.get(it.get("category", ""), it.get("category", ""))
        summary = it.get("summary", "")[:120] or "요약 준비 중"
        slug = it.get("slug") or "000"
        item_date = it.get("date", "")
        link = f"/articles/{item_date}/{slug}/" if item_date else "/articles/"
        policy_slides.append(f"""<div class="carousel-card">
          <div class="p-cat">{h.escape(cat)}</div>
          <div class="p-title">{h.escape(it.get("title","")[:50])}</div>
          <div class="p-easy"><strong>쉬운 요약</strong>{h.escape(summary)}</div>
          <div class="p-foot"><a href="{link}">자세히 &#8594;</a><span>{h.escape(it.get("source",""))}</span></div>
        </div>""")

    p_dots = "".join(f'<span class="carousel-dot{" on" if i==0 else ""}"></span>' for i in range(len(policy_slides)))

    # 오른쪽: 법령 AI (DB에서 최근 변경 3건)
    law_slides = []
    try:
        conn = sqlite3.connect(str(FINLAW_DB))
        rows = conn.execute(
            "SELECT law_id, name, revision_type, amendment_reason "
            "FROM laws WHERE revision_type != '' AND amendment_reason != '' "
            "ORDER BY enforcement_date DESC LIMIT 3"
        ).fetchall()
        conn.close()
        tag_map = {"일부개정": "edit", "전부개정": "edit", "제정": "notice"}
        for law_id, name, rev_type, reason in rows:
            tag_cls = tag_map.get(rev_type, "edit")
            law_slides.append(f"""<div class="carousel-card">
          <span class="l-tag {tag_cls}">{h.escape(rev_type)}</span>
          <div class="l-title">{h.escape(name[:40])}</div>
          <div class="l-easy"><strong>쉬운 설명</strong>{h.escape(reason[:120])}</div>
          <div class="l-foot"><a href="/finlaw/detail/{h.escape(str(law_id))}/" style="color:var(--law);text-decoration:none;font-weight:600;font-size:13px">자세히 &#8594;</a><span>{h.escape(rev_type)}</span></div>
        </div>""")
    except Exception as e:
        print(f"[home_gen] finlaw DB 에러: {e}")

    if not law_slides:
        law_slides = ["""<div class="carousel-card">
          <span class="l-tag edit">법령</span>
          <div class="l-title">금융 법령 AI</div>
          <div class="l-easy"><strong>쉬운 설명</strong>금융 법령 139건, 판례 526건을 AI가 분석합니다.</div>
          <div class="l-foot"><a href="/finlaw/" style="color:var(--law);text-decoration:none;font-weight:600;font-size:13px">전체 보기 &#8594;</a><span></span></div>
        </div>"""]

    l_dots = "".join(f'<span class="carousel-dot{" on" if i==0 else ""}"></span>' for i in range(len(law_slides)))

    return f"""<div class="twin">
  <div class="twin-col policy">
    <div class="twin-header">
      <span class="twin-badge policy">POLICY</span>
      <span class="twin-name">정부 정책 AI</span>
      <a class="twin-more" href="/policy/">전체 &#8594;</a>
    </div>
    <div class="carousel" id="c-policy">
      <div class="carousel-track" id="c-policy-track">{"".join(policy_slides)}</div>
      <div class="carousel-dots" id="c-policy-dots">{p_dots}</div>
    </div>
  </div>
  <div class="twin-col law">
    <div class="twin-header">
      <span class="twin-badge law">LAW</span>
      <span class="twin-name">금융 법령 AI</span>
      <a class="twin-more" href="/finlaw/">전체 &#8594;</a>
    </div>
    <div class="carousel" id="c-law">
      <div class="carousel-track" id="c-law-track">{"".join(law_slides)}</div>
      <div class="carousel-dots" id="c-law-dots">{l_dots}</div>
    </div>
  </div>
</div>""", len(policy_slides), len(law_slides)


def _build_dept_briefing(items: list[dict]) -> str:
    """부처별 브리핑 탭 (전체 + 부처별 필터링)"""
    by_source = defaultdict(list)
    for it in items:
        by_source[it.get("source", "")].append(it)

    top_sources = sorted(by_source.items(), key=lambda x: -len(x[1]))[:10]
    if not top_sources:
        return ""

    tabs = ['<button class="dept-tab on" type="button" data-dept="all">전체</button>']
    for src, src_items in top_sources:
        short = SHORT_SOURCE.get(src, src[:3] if len(src) > 3 else src)
        tabs.append(f'<button class="dept-tab" type="button" data-dept="{h.escape(src)}">{h.escape(short)} {len(src_items)}</button>')

    all_rows = []
    for src, src_items in top_sources:
        for it in src_items[:5]:
            imp = it.get("impact", "중")
            slug = it.get("slug") or "000"
            item_date = it.get("date", "")
            link = f"/articles/{item_date}/{slug}/" if item_date else "/articles/"
            all_rows.append(
                f'<a href="{link}" class="dept-row" data-source="{h.escape(src)}" '
                f'style="text-decoration:none;color:inherit;display:block">'
                f'<div class="dept-item">'
                f'<div class="dept-item-t">{h.escape(it.get("title","")[:80])}</div>'
                f'<span class="dept-item-imp">{h.escape(imp)}</span>'
                f'</div></a>')

    tabs_html = "".join(tabs)
    rows_html = "".join(all_rows)
    return f"""<div class="sec-hdr">부처별 브리핑</div>
  <div class="dept-tabs" id="home-dept-tabs">{tabs_html}</div>
  <div id="home-dept-list">{rows_html}</div>"""


def _policy_top_items(items: list[dict], top_indices: list[int] | None = None) -> list[dict]:
    selected = []
    if top_indices:
        for idx in top_indices:
            if 0 <= idx < len(items):
                selected.append(items[idx])
    if selected:
        return selected[:4]
    return sorted(
        items,
        key=lambda item: (-IMPACT_RANK.get(item.get("impact", "중"), 2), item.get("source", ""), item.get("title", "")),
    )[:4]


def _short_source(source: str) -> str:
    value = (source or "").strip()
    if value.endswith("위원회"):
        return value.replace("위원회", "위")
    if value.endswith("정보통신부"):
        return value.replace("정보통신부", "기부")
    if value.endswith("안전부"):
        return value.replace("안전부", "안부")
    return value[:3] if len(value) > 3 else value


def generate_policy_page(target_date: str = ""):
    """policy/index.html 동적 생성"""
    json_path = DATA_DIR / "latest.json"
    if not json_path.exists():
        print("[home_gen] latest.json 없음 — policy 생성 스킵")
        return

    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        print("[home_gen] items 없음 — policy 생성 스킵")
        return

    actual_date = data.get("target_date") or target_date or date.today().isoformat()
    dt = date.fromisoformat(actual_date)
    date_display = f"{dt.year}. {dt.month:02d}. {dt.day:02d} ({['월','화','수','목','금','토','일'][dt.weekday()]})"
    top_items = _policy_top_items(items, data.get("top3"))
    counts_by_cat = Counter(item.get("category", "행정법제") for item in items)
    counts_by_source = Counter(item.get("source", "") for item in items)
    top_sources = [src for src, _ in counts_by_source.most_common(9)]
    high_count = sum(1 for item in items if item.get("impact") == "상")

    top_cards = []
    for item in top_items:
        slug = item.get("slug", "000")
        item_date = item.get("date", actual_date)
        category = CAT_LABELS.get(item.get("category", "행정법제"), item.get("category", "기타"))
        summary = item.get("easy_summary") or item.get("summary") or item.get("why_important") or "요약이 준비 중입니다."
        top_cards.append(f"""
  <a class="card-row policy-item" data-cat="{h.escape(item.get('category','행정법제'))}" data-source="{h.escape(item.get('source',''))}" data-search="{h.escape((item.get('title','') + ' ' + summary + ' ' + ' '.join(item.get('keywords', []))).lower())}" href="/articles/{item_date}/{slug}/">
    <div class="card-left">
      <span class="card-left-tag">{h.escape(category)}</span>
      <div class="card-left-src">{h.escape(item.get('source',''))}</div>
      <div class="card-left-title">{h.escape(item.get('title',''))}</div>
      <span class="card-left-imp{' high' if item.get('impact') == '상' else ''}">영향도 {h.escape(item.get('impact','중'))}</span>
    </div>
    <div class="card-right">
      <div class="card-right-label">쉬운 요약</div>
      <div class="card-right-text">{h.escape(summary)}</div>
    </div>
  </a>""")

    top_slugs = {item.get("slug", "000") for item in top_items}
    list_cards = []
    for item in items:
        if item.get("slug", "000") in top_slugs:
            continue
        slug = item.get("slug", "000")
        item_date = item.get("date", actual_date)
        category_key = item.get("category", "행정법제")
        category = CAT_LABELS.get(category_key, category_key)
        summary = item.get("easy_summary") or item.get("summary") or item.get("why_important") or "요약이 준비 중입니다."
        keywords = " ".join(item.get("keywords", []))
        list_cards.append(f"""
  <a class="card-row policy-item" data-cat="{h.escape(category_key)}" data-source="{h.escape(item.get('source',''))}" data-search="{h.escape((item.get('title','') + ' ' + summary + ' ' + keywords).lower())}" href="/articles/{item_date}/{slug}/">
    <div class="card-left">
      <span class="card-left-tag">{h.escape(category)}</span>
      <div class="card-left-src">{h.escape(item.get('source',''))}</div>
      <div class="card-left-title">{h.escape(item.get('title',''))}</div>
      <span class="card-left-imp{' high' if item.get('impact') == '상' else ''}">영향도 {h.escape(item.get('impact','중'))}</span>
    </div>
    <div class="card-right">
      <div class="card-right-label">쉬운 요약</div>
      <div class="card-right-text">{h.escape(summary)}</div>
    </div>
  </a>""")

    cat_tabs = ['<button class="cat-tab on" type="button" data-cat="all">전체</button>']
    for key in ("금융경제", "산업기술", "사회복지", "외교안보", "행정법제"):
        cat_tabs.append(
            f'<button class="cat-tab" type="button" data-cat="{key}">{CAT_LABELS.get(key, key)} {counts_by_cat.get(key, 0)}</button>'
        )

    dept_tabs = ['<button class="dept-tab on" type="button" data-source="all">전체 기관</button>']
    for idx, source in enumerate(top_sources):
        dept_tabs.append(
            f'<button class="dept-tab" type="button" data-source="{h.escape(source)}">{h.escape(_short_source(source))}</button>'
        )

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>정부 정책 AI - 브리핑룸</title>
<meta name="description" content="대한민국 정부 보도자료를 날짜별로 정리하고 AI가 핵심만 요약합니다.">
<link rel="canonical" href="https://govbrief.kr/policy/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace;--policy:#1e40af;--policy-bg:#eff6ff;--policy-border:#bfdbfe}}
html{{scroll-behavior:smooth;-webkit-text-size-adjust:100%}}
body{{background:var(--bg);color:var(--t);font-family:var(--sans);max-width:960px;margin:0 auto;padding:58px 0 0;-webkit-font-smoothing:antialiased}}
.hdr{{position:fixed;top:0;left:0;right:0;z-index:50;max-width:960px;margin:0 auto;background:#f5f5f5;border-bottom:3px solid var(--a);height:54px;display:flex;align-items:center;padding:0 12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.logo{{font-family:var(--serif);font-size:18px;font-weight:700;color:var(--t);text-decoration:none;margin-right:10px;white-space:nowrap;flex-shrink:0}}
.hnav{{display:flex;gap:4px;align-items:center;flex:1;min-width:0;overflow-x:auto;-webkit-overflow-scrolling:touch}}
.hnav::-webkit-scrollbar{{display:none}}
.hnav a{{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--t2);text-decoration:none;padding:6px 10px;border-radius:6px;white-space:nowrap;background:var(--s);border:1px solid var(--bl);flex-shrink:0}}
.hnav a:hover{{border-color:var(--a);color:var(--a)}}
.hnav a.on-policy{{color:#fff;background:var(--policy);border-color:var(--policy);font-weight:700}}
.bell{{color:var(--m);text-decoration:none;font-family:var(--sans);font-size:11px;font-weight:600;margin-left:auto;flex-shrink:0;white-space:nowrap}}
.hero{{background:var(--policy-bg);padding:32px 24px 24px;border-bottom:1px solid var(--policy-border)}}
.hero-top{{text-align:center;margin-bottom:20px}}
.hero-top h1{{font-family:var(--serif);font-size:30px;font-weight:700;color:var(--t);margin-bottom:4px;line-height:1.35}}
.hero-date{{font-family:var(--mono);font-size:16px;font-weight:700;color:var(--t);margin-bottom:2px}}
.hero-sub{{font-family:var(--sans);font-size:14px;color:var(--m)}}
.hero-dash{{display:flex;gap:10px;margin-bottom:18px}}
.hero-stat{{flex:1;background:var(--s);border:1px solid var(--policy-border);border-radius:12px;padding:14px;text-align:center}}
.hero-stat .num{{font-family:var(--mono);font-size:30px;font-weight:700;color:var(--policy);line-height:1}}
.hero-stat .label{{font-family:var(--sans);font-size:13px;font-weight:700;color:var(--policy);margin-top:5px}}
.sbox{{max-width:100%;position:relative}}
.sbox input{{width:100%;padding:14px 16px 14px 42px;font-size:15px;border:2px solid var(--policy-border);border-radius:12px;background:#fff;color:var(--t);outline:none;font-family:var(--sans)}}
.sbox input:focus{{border-color:var(--policy)}}
.si{{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--m);font-size:16px}}
.section{{padding:22px 24px;border-bottom:1px solid var(--b)}}
.sec-hdr{{font-family:var(--serif);font-size:20px;font-weight:700;margin-bottom:14px;display:flex;align-items:baseline;justify-content:space-between}}
.sec-more{{font-family:var(--sans);font-size:12px;color:var(--a);text-decoration:none;font-weight:600}}
.cat-tabs,.dept-tabs{{display:flex;gap:5px;overflow-x:auto;margin-bottom:14px;padding-bottom:3px}}
.cat-tabs::-webkit-scrollbar,.dept-tabs::-webkit-scrollbar{{display:none}}
.cat-tab,.dept-tab{{font-family:var(--sans);padding:7px 16px;border-radius:18px;border:1.5px solid var(--bl);background:var(--s);font-size:13px;font-weight:600;color:var(--t2);white-space:nowrap;cursor:pointer}}
.cat-tab.on,.dept-tab.on{{background:var(--policy);color:#fff;border-color:var(--policy)}}
.card-row{{display:flex;gap:0;background:var(--s);border:1px solid var(--b);border-radius:12px;overflow:hidden;margin-bottom:10px;text-decoration:none;color:var(--t)}}
.card-row:hover{{border-color:var(--policy)}}
.card-left{{width:280px;flex-shrink:0;padding:16px 18px;border-right:1px solid var(--bl);display:flex;flex-direction:column;justify-content:center}}
.card-left-tag{{font-family:var(--sans);font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;display:inline-block;margin-bottom:5px;width:fit-content;background:var(--policy-bg);color:var(--policy)}}
.card-left-src{{font-family:var(--sans);font-size:11px;color:var(--m);margin-bottom:4px}}
.card-left-title{{font-family:var(--sans);font-size:16px;font-weight:700;line-height:1.45}}
.card-left-imp{{font-family:var(--mono);font-size:10px;padding:2px 6px;border-radius:3px;background:var(--al);color:var(--a);display:inline-block;margin-top:5px}}
.card-left-imp.high{{color:#dc2626;background:#fef2f2}}
.card-right{{flex:1;padding:16px 18px;display:flex;flex-direction:column;justify-content:center}}
.card-right-label{{font-family:var(--sans);font-size:10px;font-weight:700;color:var(--policy);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}}
.card-right-text{{font-family:var(--sans);font-size:15px;color:var(--t2);line-height:1.8}}
.empty{{padding:20px;border:1px dashed var(--policy-border);border-radius:12px;color:var(--m);background:#fff}}
.cta{{margin:24px;padding:18px;background:var(--a);border-radius:12px;display:flex;align-items:center;justify-content:space-between;gap:12px}}
.cta h3{{font-family:var(--serif);font-size:15px;color:#fff}}
.cta p{{font-family:var(--sans);font-size:10px;color:rgba(255,255,255,.7)}}
.cta a{{font-family:var(--sans);padding:10px 18px;background:#fff;color:var(--a);border-radius:8px;font-weight:700;font-size:12px;text-decoration:none}}
.footer{{padding:16px 24px;text-align:center;font-family:var(--sans);font-size:10px;color:var(--m)}}
.footer a{{color:var(--t);text-decoration:none;font-weight:600}}
@media(max-width:768px){{body{{padding-top:48px}}.hdr{{height:48px;padding:0 10px}}.logo{{font-size:16px;margin-right:8px}}.hnav{{gap:3px}}.hnav a{{font-size:11px;padding:5px 7px}}.hero{{padding:22px 16px 18px}}.hero-top h1{{font-size:22px}}.hero-stat{{padding:12px 6px}}.hero-stat .num{{font-size:22px}}.hero-stat .label{{font-size:11px}}.section{{padding:18px 16px}}.card-row{{flex-direction:column}}.card-left{{width:auto;border-right:none;border-bottom:1px solid var(--bl)}}.cta{{margin:18px 16px}}}}
</style>
</head>
<body>
<header class="hdr">
  <a class="logo" href="/">브리핑룸</a>
  <nav class="hnav">
    <a href="/">홈</a>
    <a class="on-policy" href="/policy/">정부 정책 AI</a>
    <a href="/finlaw/">금융 법령 AI</a>
    <a href="/articles/">아카이브</a>
  </nav>
  <a class="bell" href="https://t.me/govbrief" target="_blank">알림</a>
</header>
<section class="hero">
  <div class="hero-top">
    <h1>정부 정책 AI</h1>
    <div class="hero-date">{date_display}</div>
    <div class="hero-sub">최신 스냅샷 기준 정책 보도자료 브리핑</div>
  </div>
  <div class="hero-dash">
    <div class="hero-stat"><div class="num">{len(items)}</div><div class="label">발표 건수</div></div>
    <div class="hero-stat"><div class="num">{len(counts_by_source)}</div><div class="label">참여 기관</div></div>
    <div class="hero-stat"><div class="num">{high_count}</div><div class="label">영향도 상</div></div>
    <div class="hero-stat"><div class="num">{sum(counts_by_cat.values())}</div><div class="label">스냅샷 항목</div></div>
  </div>
  <div class="sbox">
    <span class="si">&#x2315;</span>
    <input id="policy-search" placeholder="보도자료 제목, 부처명, 키워드로 검색..." autocomplete="off">
  </div>
</section>
<section class="section">
  <div class="sec-hdr">핵심 브리핑 <a class="sec-more" href="/articles/">전체 {len(items)}건 &#8594;</a></div>
  <div>{"".join(top_cards)}</div>
</section>
<section class="section">
  <div class="sec-hdr">전체 정책 브리핑</div>
  <div class="cat-tabs" id="cat-tabs">{"".join(cat_tabs)}</div>
  <div id="policy-list">{"".join(list_cards)}</div>
  <div id="policy-empty" class="empty" style="display:none">조건에 맞는 정책 브리핑이 없습니다.</div>
</section>
<section class="section">
  <div class="sec-hdr">부처별 빠른 보기</div>
  <div class="dept-tabs" id="dept-tabs">{"".join(dept_tabs)}</div>
</section>
<div class="cta">
  <div><h3>매일 오전 최신 정책 브리핑</h3><p>텔레그램으로 날짜 기준 브리핑을 받아보세요.</p></div>
  <a href="https://t.me/govbrief" target="_blank" rel="noopener">무료 구독</a>
</div>
<div class="footer"><a href="/">홈</a> · <a href="/policy/">정부 정책 AI</a> · <a href="/finlaw/">금융 법령 AI</a> · <a href="/articles/">아카이브</a> · <a href="https://t.me/govbrief" target="_blank">텔레그램</a><br>govbrief.kr</div>
<script>
const policySearch = document.getElementById('policy-search');
const policyItems = Array.from(document.querySelectorAll('.policy-item'));
const emptyState = document.getElementById('policy-empty');
const catTabs = Array.from(document.querySelectorAll('#cat-tabs .cat-tab'));
const deptTabs = Array.from(document.querySelectorAll('#dept-tabs .dept-tab'));
let currentCat = 'all';
let currentSource = 'all';

function applyPolicyFilters() {{
  const q = policySearch.value.trim().toLowerCase();
  let visible = 0;
  policyItems.forEach((item) => {{
    const matchCat = currentCat === 'all' || item.dataset.cat === currentCat;
    const matchSource = currentSource === 'all' || item.dataset.source === currentSource;
    const matchSearch = !q || item.dataset.search.includes(q) || item.dataset.source.toLowerCase().includes(q);
    const show = matchCat && matchSource && matchSearch;
    item.style.display = show ? '' : 'none';
    if (show) visible += 1;
  }});
  emptyState.style.display = visible ? 'none' : '';
}}

catTabs.forEach((tab) => tab.addEventListener('click', () => {{
  currentCat = tab.dataset.cat;
  catTabs.forEach((node) => node.classList.toggle('on', node === tab));
  applyPolicyFilters();
}}));

deptTabs.forEach((tab) => tab.addEventListener('click', () => {{
  currentSource = tab.dataset.source;
  deptTabs.forEach((node) => node.classList.toggle('on', node === tab));
  applyPolicyFilters();
}}));

policySearch.addEventListener('input', applyPolicyFilters);
applyPolicyFilters();
</script>
</body>
</html>"""

    POLICY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    POLICY_INDEX_PATH.write_text(page, encoding="utf-8")
    print(f"[home_gen] policy/index.html 생성 — {len(items)}건")


def generate_home(target_date: str = ""):
    """index.html 동적 생성"""
    if not target_date:
        target_date = date.today().isoformat()

    # 데이터 로드
    json_path = DATA_DIR / "latest.json"
    if not json_path.exists():
        print("[home_gen] latest.json 없음")
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    if not items:
        print("[home_gen] items 없음")
        return

    actual_date = data.get("target_date", target_date)
    date_display = actual_date.replace("-", ".")

    # CSS 직접 정의 (파이프라인 재생성 시에도 깨지지 않도록)
    css = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace;
--policy:#1e40af;--policy-bg:#eff6ff;--policy-border:#bfdbfe;
--law:#047857;--law-bg:#ecfdf5;--law-border:#a7f3d0}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--t);font-family:var(--sans);max-width:960px;margin:0 auto;padding:58px 0 0;-webkit-font-smoothing:antialiased}
.hdr{position:fixed;top:0;left:0;right:0;z-index:50;max-width:960px;margin:0 auto;background:#f5f5f5;border-bottom:3px solid var(--a);height:54px;display:flex;align-items:center;padding:0 12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.logo{font-family:var(--serif);font-size:18px;font-weight:700;color:var(--t);text-decoration:none;margin-right:10px;white-space:nowrap;flex-shrink:0}
.hnav{display:flex;gap:4px;align-items:center;flex:1;min-width:0;overflow-x:auto;-webkit-overflow-scrolling:touch}
.hnav::-webkit-scrollbar{display:none}
.hnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--t2);text-decoration:none;padding:6px 10px;border-radius:6px;white-space:nowrap;background:var(--s);border:1px solid var(--bl);flex-shrink:0}
.hnav a:hover{border-color:var(--a);color:var(--a)}
.hnav a.on{color:#fff;background:var(--a);border-color:var(--a);font-weight:700}
.hnav a.on-policy{color:#fff;background:var(--policy);border-color:var(--policy);font-weight:700}
.hnav a.on-law{color:#fff;background:var(--law);border-color:var(--law);font-weight:700}
.bell{color:var(--m);text-decoration:none;font-family:var(--sans);font-size:11px;font-weight:600;margin-left:auto;flex-shrink:0;white-space:nowrap}
.hero{background:#efefef;padding:28px 24px 22px;text-align:center;border-bottom:1px solid var(--b)}
.hero h1{font-family:var(--serif);font-size:30px;font-weight:700;margin-bottom:6px;line-height:1.35}
.hero p{font-family:var(--sans);font-size:15px;color:var(--m);margin-bottom:16px}
.sbox{max-width:560px;margin:0 auto;position:relative}
.sbox input{width:100%;padding:15px 16px 15px 44px;font-size:16px;border:2px solid var(--b);border-radius:12px;background:#fff;color:var(--t);outline:none;font-family:var(--sans)}
.sbox input::placeholder{color:var(--m)}
.sbox input:focus{border-color:var(--a)}
.si{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:var(--m);font-size:16px}
.tags{display:flex;gap:6px;margin-top:10px;justify-content:center;flex-wrap:wrap}
.tags span{font-size:12px;color:var(--t2);border:1px solid var(--b);padding:5px 14px;border-radius:18px;background:#fff;cursor:pointer}
.tags span:hover{border-color:var(--a);color:var(--a)}
.svcs{display:flex;gap:12px;padding:18px 24px 0}
.svc{flex:1;background:var(--s);border:2px solid var(--b);border-radius:12px;padding:18px;text-decoration:none;color:var(--t);display:flex;gap:12px;align-items:center;justify-content:center;text-align:center}
.svc:first-child{border-color:var(--a)}
.svc .tt{font-size:20px;font-weight:700;font-family:var(--serif)}
.svc .dd{font-size:12px;color:var(--t2);margin-top:3px}
.sec{padding:0 24px;margin-top:24px}
.sec-hdr{font-family:var(--serif);font-size:20px;font-weight:700;margin-bottom:14px;display:flex;align-items:baseline;justify-content:space-between}
.sec-more{font-size:11px;color:var(--a);text-decoration:none;font-weight:600}
.divider{height:1px;background:var(--b);margin:24px 24px 0}
.twin{display:flex;gap:0}
.twin-col{flex:1;min-width:0;padding:22px 24px;display:flex;flex-direction:column}
.twin-col.policy{background:var(--policy-bg);border-right:1px solid var(--policy-border)}
.twin-col.law{background:var(--law-bg)}
.twin-header{display:flex;align-items:center;gap:8px;margin-bottom:14px}
.twin-badge{font-family:var(--mono);font-size:10px;font-weight:700;padding:3px 10px;border-radius:6px;text-transform:uppercase;letter-spacing:.05em}
.twin-badge.policy{background:var(--policy);color:#fff}
.twin-badge.law{background:var(--law);color:#fff}
.twin-name{font-family:var(--serif);font-size:20px;font-weight:700}
.twin-more{font-family:var(--sans);font-size:12px;color:var(--a);text-decoration:none;font-weight:600;margin-left:auto}
.p-cat{font-family:var(--sans);font-size:11px;font-weight:700;color:var(--policy);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}
.p-title{font-family:var(--serif);font-size:18px;font-weight:700;line-height:1.45;margin-bottom:10px}
.p-easy{font-family:var(--sans);font-size:15px;color:var(--t2);line-height:1.75;padding:12px 14px;background:var(--policy-bg);border-left:3px solid var(--policy);border-radius:0 8px 8px 0;margin-bottom:10px;flex:1}
.p-easy strong{display:block;font-size:10px;color:var(--policy);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}
.p-foot{display:flex;justify-content:space-between;align-items:center;font-family:var(--sans);font-size:12px;color:var(--m)}
.p-foot a{color:var(--policy);text-decoration:none;font-weight:600;font-size:13px}
.l-tag{display:inline-block;font-family:var(--sans);font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;margin-bottom:6px}
.l-tag.edit{background:#eef2ff;color:#3730a3}
.l-tag.case{background:#fff7ed;color:#9a3412}
.l-tag.notice{background:#ecfdf5;color:#065f46}
.l-title{font-family:var(--serif);font-size:18px;font-weight:700;line-height:1.45;margin-bottom:10px}
.l-easy{font-family:var(--sans);font-size:15px;color:var(--t2);line-height:1.75;padding:12px 14px;background:var(--law-bg);border-left:3px solid var(--law);border-radius:0 8px 8px 0;margin-bottom:10px;flex:1}
.l-easy strong{display:block;font-size:10px;color:var(--law);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}
.l-foot{display:flex;justify-content:space-between;align-items:center;font-family:var(--sans);font-size:12px;color:var(--m)}
.carousel{position:relative;overflow:hidden;border-radius:14px;border:2px solid var(--b);background:var(--s)}
.carousel-track{display:flex;transition:transform .3s ease}
.carousel-card{min-width:100%;padding:24px}
.carousel-dots{display:flex;justify-content:center;gap:6px;padding:10px 0}
.carousel-dot{width:8px;height:8px;border-radius:50%;background:var(--bl);cursor:pointer;transition:background .2s}
.carousel-dot.on{background:var(--a)}
.sum-label{font-size:10px;font-weight:700;color:var(--a);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.sum-title{font-family:var(--serif);font-size:18px;font-weight:700;line-height:1.5;margin-bottom:10px}
.sum-kw{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.sum-kw span{font-size:12px;font-weight:700;color:var(--a);background:var(--al);border:1px solid var(--ab);padding:4px 12px;border-radius:16px}
.sum-body{font-size:14px;color:var(--t2);line-height:1.8;margin-bottom:12px}
.sum-foot{display:flex;align-items:center;justify-content:space-between}
.sum-foot a{font-size:12px;color:var(--a);text-decoration:none;font-weight:600}
.sum-foot span{font-family:var(--mono);font-size:10px;color:var(--m)}
.dept-tabs{display:flex;gap:5px;overflow-x:auto;margin-bottom:10px;padding-bottom:4px}
.dept-tabs::-webkit-scrollbar{display:none}
.dept-tab{padding:7px 14px;border-radius:20px;border:2px solid var(--bl);background:var(--s);font-size:12px;font-weight:600;color:var(--t2);white-space:nowrap;cursor:pointer}
.dept-tab.on{background:var(--a);color:#fff;border-color:var(--a)}
.dept-item{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--bl)}
.dept-item:last-child{border-bottom:none}
.dept-item-t{font-size:14px;font-weight:600;flex:1;margin-right:8px;line-height:1.4}
.dept-item-imp{font-family:var(--mono);font-size:9px;padding:2px 6px;border-radius:3px;background:var(--al);color:var(--a);white-space:nowrap}
.cta{margin:24px;padding:20px;background:var(--a);border-radius:12px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.cta h3{font-family:var(--serif);font-size:16px;color:#fff}
.cta p{font-size:11px;color:rgba(255,255,255,.6)}
.cta a{padding:11px 20px;background:#fff;color:var(--a);border-radius:8px;font-weight:700;font-size:13px;text-decoration:none;white-space:nowrap}
.footer{padding:20px 24px;text-align:center;font-size:10px;color:var(--m)}
.footer a{color:var(--t);text-decoration:none;font-weight:600}
.bnav{display:none;position:fixed;bottom:0;left:0;right:0;z-index:50;height:58px;background:#fff;border-top:2px solid var(--b);grid-template-columns:repeat(5,1fr);align-items:center;max-width:960px;margin:0 auto}
.bnav a{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--m);font-size:10px;font-weight:600}
.bnav a.on{color:var(--a)}
.bnav a span:first-child{font-size:22px}
@media(max-width:768px){
  body{padding-top:48px;padding-bottom:62px}
  .hdr{height:48px;padding:0 10px}
  .logo{font-size:16px;margin-right:8px}
  .hnav{gap:3px}
  .hnav a{font-size:11px;padding:5px 7px}
  .hero{padding:24px 16px 18px}
  .hero h1{font-size:22px}
  .hero p{font-size:12px;margin-bottom:14px}
  .sbox input{padding:12px 14px 12px 38px;font-size:14px}
  .tags span{font-size:11px;padding:4px 10px}
  .svcs{padding:12px 16px 0;gap:8px}
  .svc{padding:12px;gap:8px}
  .svc .tt{font-size:13px}
  .svc .dd{font-size:9px}
  .sec{padding:0 16px;margin-top:18px}
  .sec-hdr{font-size:17px;margin-bottom:10px}
  .divider{margin:18px 16px 0}
  .carousel-card{padding:18px 16px}
  .sum-title{font-size:16px}
  .sum-body{font-size:13px}
  .twin{flex-direction:column}
  .twin-col{padding:18px 16px}
  .twin-col.policy{border-right:none;border-bottom:1px solid var(--policy-border)}
  .cta{margin:18px 16px;padding:16px}
  .cta h3{font-size:14px}
  .bnav{display:grid}
}
"""

    # 캐러셀 생성
    policy_carousel, c1_count = _build_policy_carousel(items, actual_date)
    dept_briefing = _build_dept_briefing(items)
    twin_html, twin_p_count, twin_l_count = _build_twin_carousel(items, date_display)

    # 검색 태그 (상위 키워드)
    all_kws = []
    for it in items[:30]:
        for kw in (it.get("keywords") or []):
            if kw and f"#{kw}" not in all_kws and len(all_kws) < 4:
                all_kws.append(f"#{kw}")
    tags_html = "".join(f"<span>{h.escape(k)}</span>" for k in all_kws)

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>govbrief.kr — 정부 정책 + 금융법령 통합 인텔리전스</title>
<meta name="description" content="대한민국 51개 정부 부처 보도자료 AI 요약 + 금융법령 모니터링.">
<link rel="canonical" href="https://govbrief.kr/">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#fafafa">
<link rel="apple-touch-icon" href="/icon-192.svg">
<link rel="alternate" type="application/rss+xml" title="브리핑룸 RSS" href="https://govbrief.kr/feed/rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>

<header class="hdr">
  <a class="logo" href="/">브리핑룸</a>
  <nav class="hnav">
    <a class="on" href="/">홈</a>
    <a href="/policy/">정부 정책 AI</a>
    <a href="/finlaw/">금융 법령 AI</a>
    <a href="/articles/">아카이브</a>
  </nav>
  <a class="bell" href="https://t.me/govbrief" target="_blank">알림</a>
</header>

<section class="hero">
  <h1>정부가 발표하면,<br>AI가 해석합니다</h1>
  <p>정부 정책 · 금융 법령 · 입법 예고, 핵심만 브리핑</p>
  <div class="sbox" style="position:relative">
    <span class="si">⌕</span>
    <input id="search-input" placeholder="정책이나 법령에 대해 물어보세요..." autocomplete="off">
    <div id="search-results" style="display:none;position:absolute;top:100%;left:0;right:0;z-index:40;margin-top:6px;background:#fff;border:1px solid var(--b);border-radius:10px;max-height:360px;overflow-y:auto;box-shadow:0 4px 16px rgba(0,0,0,.1)"></div>
  </div>
  <div class="tags">{tags_html}</div>
</section>

{twin_html}

<div class="divider"></div>
<section class="sec" id="policy-summary">
  {policy_carousel}
</section>

<div class="divider"></div>
<section class="sec" id="dept-briefing">
  {dept_briefing}
</section>

<div class="cta"><div><h3>매일 3분 브리핑</h3><p>텔레그램에서 받아보세요</p></div><a href="https://t.me/govbrief" target="_blank">구독</a></div>

<div class="footer"><a href="/">홈</a> · <a href="/policy/">정부 정책 AI</a> · <a href="/finlaw/">금융 법령 AI</a> · <a href="/articles/">아카이브</a> · <a href="https://t.me/govbrief" target="_blank">텔레그램</a><br>govbrief.kr</div>

<nav class="bnav"><a class="on" href="/"><span style="font-size:16px;font-weight:700">B</span>브리핑</a><a href="javascript:void(0)" onclick="document.getElementById('search-input').focus();window.scrollTo(0,0)"><span style="font-size:16px">⌕</span>검색</a><a href="/articles/"><span style="font-size:16px">≡</span>달력</a><a href="/finlaw/"><span style="font-size:16px;font-weight:700">L</span>법령AI</a><a href="https://t.me/govbrief"><span style="font-size:16px">→</span>알림</a></nav>

<script>
function makeCarousel(id, count) {{
  let cur = 0;
  const track = document.getElementById(id + '-track');
  const dots = document.getElementById(id + '-dots').children;
  const el = document.getElementById(id);
  function go(n) {{
    cur = Math.max(0, Math.min(count - 1, n));
    track.style.transform = `translateX(-${{cur * 100}}%)`;
    Array.from(dots).forEach((d, i) => d.classList.toggle('on', i === cur));
  }}
  Array.from(dots).forEach((d, i) => d.addEventListener('click', () => go(i)));
  let startX = 0;
  el.addEventListener('touchstart', e => {{ startX = e.touches[0].clientX }}, {{ passive: true }});
  el.addEventListener('touchend', e => {{
    const diff = startX - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 40) go(cur + (diff > 0 ? 1 : -1));
  }}, {{ passive: true }});
}}
makeCarousel('c1', {c1_count});
makeCarousel('c-policy', {twin_p_count});
makeCarousel('c-law', {twin_l_count});

const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
let searchTimer;
searchInput.addEventListener('input', function() {{
  clearTimeout(searchTimer);
  const q = this.value.trim();
  if (q.length < 2) {{ searchResults.style.display = 'none'; return; }}
  searchTimer = setTimeout(() => doSearch(q), 300);
}});
searchInput.addEventListener('keydown', function(e) {{
  if (e.key === 'Enter' && !e.isComposing) {{
    const q = this.value.trim();
    if (q) window.location.href = '/tools/finlaw-gpt/?q=' + encodeURIComponent(q);
  }}
}});
const SB_URL='https://jxoghnttelexnfoeepbz.supabase.co';
const SB_KEY='sb_publishable_r3eTQXF419LfIiPdE17gyw_zvAQFd5s';
const SB_HDR={{'apikey':SB_KEY,'Authorization':'Bearer '+SB_KEY}};
function renderResults(items,query){{
  const typeLabel={{law:'법령',article:'조문',precedent:'판례'}};
  searchResults.textContent='';
  const cta=document.createElement('a');
  cta.href='/tools/finlaw-gpt/?q='+encodeURIComponent(query);
  cta.style.cssText='display:block;padding:12px 16px;text-align:center;font-size:13px;color:#d96c2c;font-weight:600;text-decoration:none';
  cta.textContent=items.length?'FinLaw GPT에서 상세 질문 \u2192':'FinLaw GPT에게 질문하기 \u2192';
  if(items.length){{
    items.forEach(item=>{{
      const link=document.createElement('a');
      link.href=item.link||'/tools/finlaw-gpt/?q='+encodeURIComponent(query);
      link.style.cssText='display:block;padding:12px 16px;border-bottom:1px solid #e0e0e0;text-decoration:none;color:#222';
      const top=document.createElement('div');top.style.cssText='display:flex;align-items:center;gap:8px';
      const badge=document.createElement('span');badge.style.cssText='font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;background:rgba(217,108,44,.06);color:#d96c2c';
      badge.textContent=typeLabel[item.type]||item.type||'';
      const title=document.createElement('span');title.style.cssText='font-size:14px;font-weight:600';
      title.textContent=String(item.title||'').slice(0,60);
      top.appendChild(badge);top.appendChild(title);
      const sub=document.createElement('div');sub.style.cssText='font-size:12px;color:#999;margin-top:3px';
      sub.textContent=String(item.subtitle||'').slice(0,80);
      link.appendChild(top);link.appendChild(sub);
      searchResults.appendChild(link);
    }});
  }}else{{
    const empty=document.createElement('div');empty.style.cssText='padding:16px;text-align:center;font-size:13px;color:#999';
    empty.textContent='금융법령(139건) 내 검색 결과 없음. 일반 법령은 법제처 국가법령정보센터를 이용하세요.';
    searchResults.appendChild(empty);
  }}
  searchResults.appendChild(cta);searchResults.style.display='block';
}}
function searchSupabase(query){{
  const kw='%'+query+'%';
  return Promise.all([
    fetch(SB_URL+'/rest/v1/laws?or=(name.ilike.'+encodeURIComponent(kw)+',amendment_reason.ilike.'+encodeURIComponent(kw)+')&select=law_id,name,ministry,law_type&limit=5',{{headers:SB_HDR}}).then(r=>r.json()),
    fetch(SB_URL+'/rest/v1/articles?or=(article_title.ilike.'+encodeURIComponent(kw)+',content.ilike.'+encodeURIComponent(kw)+')&select=id,law_id,article_no,article_title&limit=5',{{headers:SB_HDR}}).then(r=>r.json()),
    fetch(SB_URL+'/rest/v1/precedents?or=(case_name.ilike.'+encodeURIComponent(kw)+',summary.ilike.'+encodeURIComponent(kw)+')&select=prec_id,case_name,court,decision_date&limit=5',{{headers:SB_HDR}}).then(r=>r.json())
  ]).then(res=>{{
    const items=[];
    (res[0]||[]).forEach(r=>items.push({{type:'law',title:r.name,subtitle:(r.ministry||'')+' '+(r.law_type||''),link:'/finlaw/detail/'+r.law_id+'/'}}));
    (res[1]||[]).forEach(r=>items.push({{type:'article',title:(r.article_no?'제'+r.article_no+'조 ':'')+(r.article_title||''),subtitle:'',link:'/finlaw/detail/'+r.law_id+'/'}}));
    (res[2]||[]).forEach(r=>items.push({{type:'precedent',title:r.case_name,subtitle:(r.court||'')+' '+(r.decision_date||''),link:'/finlaw/cases/'+r.prec_id+'/'}}));
    return items;
  }});
}}
async function doSearch(query){{
  try{{
    const r=await fetch('https://govbrief-api.vercel.app/api/search',{{
      method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{query}}),
    }});
    const data=await r.json();
    if(data.results&&data.results.length){{
      const items=data.results.map(item=>{{
        let link='/tools/finlaw-gpt/?q='+encodeURIComponent(query);
        try{{const u=new URL(String(item.link||''),location.origin);if(u.protocol==='http:'||u.protocol==='https:')link=u.href;}}catch(e){{}}
        return{{type:item.type,title:item.title,subtitle:item.subtitle,link}};
      }});
      renderResults(items,query);
    }}else{{
      const items=await searchSupabase(query);
      renderResults(items,query);
    }}
  }}catch(e){{
    try{{const items=await searchSupabase(query);renderResults(items,query);}}
    catch(e2){{renderResults([],query);}}
  }}
}}
document.addEventListener('click', function(e) {{
  if (!e.target.closest('.sbox')) searchResults.style.display = 'none';
}});

// 부처별 브리핑 필터링
(function(){{
  const tabs=document.querySelectorAll('#home-dept-tabs .dept-tab');
  const rows=document.querySelectorAll('#home-dept-list .dept-row');
  if(!tabs.length) return;
  tabs.forEach(function(tab){{
    tab.addEventListener('click',function(){{
      tabs.forEach(function(t){{t.classList.remove('on')}});
      tab.classList.add('on');
      const dept=tab.getAttribute('data-dept');
      rows.forEach(function(r){{
        r.style.display=(dept==='all'||r.getAttribute('data-source')===dept)?'block':'none';
      }});
    }});
  }});
}})();
</script>

</body>
</html>"""

    INDEX_PATH.write_text(page, encoding="utf-8")
    print(f"[home_gen] index.html 생성 — {len(items)}건, 캐러셀 {c1_count}슬라이드")


def main():
    generate_home()


if __name__ == "__main__":
    main()
