"""홈 페이지(index.html) 동적 생성

latest.json에서 데이터를 읽어 캐러셀, 부처별 브리핑 등을 자동 생성합니다.

실행: python -m briefingroom.home_gen
"""
from __future__ import annotations

import html as h
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from briefingroom.config import BASE_DIR, DATA_DIR

INDEX_PATH = BASE_DIR / "index.html"

# 카테고리 한글명
CAT_LABELS = {
    "금융경제": "금융·경제",
    "산업기술": "산업·기술",
    "사회복지": "사회·복지",
    "외교안보": "외교·안보",
    "행정법제": "행정·법제",
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

    return f"""<div class="sec-hdr">오늘의 정책 요약 <span style="font-family:var(--mono);font-size:11px;color:var(--m);font-weight:400;margin-left:6px">{date_display}</span><a class="sec-more" href="/articles/">전체 {len(items)}건 →</a></div>
  <div class="carousel" id="c1">
    <div class="carousel-track" id="c1-track">
      {"".join(slides)}
    </div>
    <div class="carousel-dots" id="c1-dots">{dots}</div>
  </div>""", slide_count


def _build_dept_briefing(items: list[dict]) -> str:
    """부처별 브리핑 탭"""
    by_source = defaultdict(list)
    for it in items:
        by_source[it.get("source", "")].append(it)

    # 상위 7개 부처
    top_sources = sorted(by_source.items(), key=lambda x: -len(x[1]))[:7]
    if not top_sources:
        return ""

    tabs = []
    for i, (src, _) in enumerate(top_sources):
        short = src[:3]
        cls = ' on' if i == 0 else ''
        tabs.append(f'<span class="dept-tab{cls}">{h.escape(short)}</span>')

    # 첫 번째 부처 항목
    first_items = top_sources[0][1][:5]
    rows = []
    for it in first_items:
        imp = it.get("impact", "중")
        slug = it.get("slug") or "000"
        date = it.get("date", "")
        link = f"/articles/{date}/{slug}/" if date else "/articles/"
        rows.append(f'<a href="{link}" style="text-decoration:none;color:inherit"><div class="dept-item"><div class="dept-item-t">{h.escape(it.get("title","")[:60])}</div><span class="dept-item-imp">{h.escape(imp)}</span></div></a>')

    return f"""<div class="sec-hdr">부처별 브리핑</div>
  <div class="dept-tabs">{"".join(tabs)}</div>
  <div>{"".join(rows)}</div>"""


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

    # CSS 읽기
    css = _read_current_css()

    # 캐러셀 생성
    policy_carousel, c1_count = _build_policy_carousel(items, actual_date)
    dept_briefing = _build_dept_briefing(items)

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
    <a href="/finlaw/">금융 법령 AI</a>
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

<div class="svcs">
  <a class="svc" href="/"><div><div class="tt">홈</div><div class="dd">51개 부처 · 일 {len(items)}건 · AI 분석</div></div></a>
  <a class="svc" href="/finlaw/"><div><div class="tt">금융 법령 AI</div><div class="dd">139법령 · 526판례 · 검색</div></div></a>
</div>

<div class="divider"></div>
<section class="sec" id="policy-summary">
  {policy_carousel}
</section>

<div class="divider"></div>
<section class="sec" id="dept-briefing">
  {dept_briefing}
</section>

<div class="cta"><div><h3>매일 3분 브리핑</h3><p>텔레그램에서 받아보세요</p></div><a href="https://t.me/govbrief" target="_blank">구독</a></div>

<div class="footer"><a href="/">홈</a> · <a href="/finlaw/">금융 법령 AI</a> · <a href="https://t.me/govbrief" target="_blank">텔레그램</a><br>govbrief.kr</div>

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
async function doSearch(query) {{
  try {{
    const r = await fetch('https://govbrief-api.vercel.app/api/search', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{query}}),
    }});
    const data = await r.json();
    const typeLabel = {{law: '법령', article: '조문', precedent: '판례'}};
    const safeUrl = (value) => {{
      try {{
        const url = new URL(String(value || ''), window.location.origin);
        if (url.protocol === 'http:' || url.protocol === 'https:') return url.href;
      }} catch (e) {{}}
      return '/tools/finlaw-gpt/?q=' + encodeURIComponent(query);
    }};
    const cta = document.createElement('a');
    cta.href = '/tools/finlaw-gpt/?q=' + encodeURIComponent(query);
    cta.style.cssText = 'display:block;padding:12px 16px;text-align:center;font-size:13px;color:#d96c2c;font-weight:600;text-decoration:none';
    cta.textContent = data.results && data.results.length ? 'FinLaw GPT에서 상세 질문 →' : 'FinLaw GPT에게 질문하기 →';
    searchResults.textContent = '';
    if (data.results && data.results.length) {{
      data.results.forEach(item => {{
        const link = document.createElement('a');
        link.href = safeUrl(item.link);
        link.style.cssText = 'display:block;padding:12px 16px;border-bottom:1px solid #e0e0e0;text-decoration:none;color:#222';
        const top = document.createElement('div');
        top.style.cssText = 'display:flex;align-items:center;gap:8px';
        const badge = document.createElement('span');
        badge.style.cssText = 'font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;background:rgba(217,108,44,.06);color:#d96c2c';
        badge.textContent = typeLabel[item.type] || '';
        const title = document.createElement('span');
        title.style.cssText = 'font-size:14px;font-weight:600';
        title.textContent = String(item.title || '').slice(0,50);
        const subtitle = document.createElement('div');
        subtitle.style.cssText = 'font-size:12px;color:#999;margin-top:3px';
        subtitle.textContent = String(item.subtitle || '').slice(0,60);
        top.appendChild(badge);
        top.appendChild(title);
        link.appendChild(top);
        link.appendChild(subtitle);
        searchResults.appendChild(link);
      }});
      searchResults.appendChild(cta);
      searchResults.style.display = 'block';
    }} else {{
      const empty = document.createElement('div');
      empty.style.cssText = 'padding:16px;text-align:center;font-size:13px;color:#999';
      empty.textContent = '검색 결과 없음';
      searchResults.appendChild(empty);
      searchResults.appendChild(cta);
      searchResults.style.display = 'block';
    }}
  }} catch(e) {{ console.error(e); }}
}}
document.addEventListener('click', function(e) {{
  if (!e.target.closest('.sbox')) searchResults.style.display = 'none';
}});
</script>

</body>
</html>"""

    INDEX_PATH.write_text(page, encoding="utf-8")
    print(f"[home_gen] index.html 생성 — {len(items)}건, 캐러셀 {c1_count}슬라이드")


def main():
    generate_home()


if __name__ == "__main__":
    main()
