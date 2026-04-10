"""articles/index.html 생성 — 주간 그룹핑 + 더보기 + 주간 시그널 연동

실행: python -m briefingroom.articles_gen
"""
from __future__ import annotations

import html as h
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from briefingroom.config import BASE_DIR, DATA_DIR
from briefingroom.site_templates import (
    SITE_BASE_CSS, SITE_NAV_CSS, SITE_FONT_LINKS,
    render_top_nav, render_footer,
)

ARTICLES_DIR = BASE_DIR / "articles"

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

# ── 추가 CSS ────────────────────────────────────────────
_PAGE_CSS = """
.hero-archive{background:#fff8f3;padding:32px 24px 24px;border-bottom:1px solid var(--ab)}
.hero-archive .hero-top{text-align:center;margin-bottom:20px}
.hero-archive h1{font-family:var(--serif);font-size:28px;font-weight:700;margin-bottom:6px;line-height:1.35}
.hero-archive .hero-sub{font-size:14px;color:var(--m)}
.hero-dash{display:flex;gap:10px;margin-bottom:16px}
.hero-stat{flex:1;background:var(--s);border:1px solid var(--ab);border-radius:12px;padding:14px;text-align:center}
.hero-stat .num{font-family:var(--mono);font-size:28px;font-weight:700;color:var(--a);line-height:1}
.hero-stat .label{font-size:12px;font-weight:700;color:var(--a);margin-top:5px}
.sbox{max-width:460px;margin:0 auto;position:relative}
.sbox input{width:100%;padding:13px 16px 13px 40px;font-size:15px;border:2px solid var(--b);border-radius:12px;background:#fff;color:var(--t);outline:none;font-family:var(--sans)}
.sbox input::placeholder{color:var(--m)}
.sbox input:focus{border-color:var(--a)}
.si{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--m);font-size:16px}
.week-group{margin:0 24px 24px}
.week-header{display:flex;align-items:center;justify-content:space-between;padding:18px 0 12px;border-bottom:2px solid var(--a)}
.week-label{font-family:var(--serif);font-size:18px;font-weight:700}
.week-range{font-family:var(--mono);font-size:13px;color:var(--m)}
.week-total{font-family:var(--mono);font-size:13px;font-weight:700;color:var(--a)}
.week-total-link{font-size:12px;color:var(--a);font-weight:600;text-decoration:none;margin-left:6px;padding:4px 10px;border:1px solid var(--a);border-radius:6px}
.week-total-link:hover{background:var(--a);color:#fff}
.week-more{display:block;width:100%;padding:14px 0;margin-top:12px;background:none;border:1px dashed var(--a);border-radius:8px;font-family:var(--sans);font-size:13px;font-weight:600;color:var(--a);cursor:pointer;text-align:center}
.week-more:hover{background:var(--al)}
.week-hidden{display:none}
.day-card{background:var(--s);border:1px solid var(--b);border-radius:12px;padding:18px;margin-top:12px}
.day-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.day-date{font-family:var(--serif);font-size:17px;font-weight:700}
.day-dow{font-size:12px;color:var(--m);margin-left:6px}
.day-count{font-family:var(--mono);font-size:12px;color:var(--a);font-weight:700}
.day-cats{font-size:11px;color:var(--t2);margin-bottom:10px}
.day-item{display:block;padding:9px 0;border-top:1px dashed var(--bl);text-decoration:none;color:var(--t);font-size:13px;line-height:1.5}
.day-item:first-of-type{border-top:none}
.day-imp{font-family:var(--mono);font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;margin-right:6px}
.day-imp-h{background:#fee2e2;color:#dc2626}
.day-imp-m{background:#fef3c7;color:#d97706}
.day-imp-l{background:#f3f4f6;color:#6b7280}
.day-src{color:var(--m);margin-right:4px}
.day-more{display:block;width:100%;padding:12px 0;margin-top:6px;background:none;border:1px dashed var(--b);border-radius:8px;font-family:var(--sans);font-size:13px;font-weight:600;color:var(--t2);cursor:pointer;text-align:center}
.day-more:hover{border-color:var(--a);color:var(--a)}
.day-hidden{display:none}
.week-report{display:block;margin-top:14px;background:var(--policy-bg);border:1px solid var(--policy-border);border-radius:10px;padding:16px;text-decoration:none;color:var(--t)}
.week-report:hover{border-color:var(--policy)}
.week-report-head{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.week-report-badge{font-family:var(--mono);font-size:10px;font-weight:700;color:#fff;background:var(--policy);padding:3px 8px;border-radius:4px}
.week-report-title{font-size:14px;font-weight:700}
.week-report-arrow{margin-left:auto;color:var(--policy);font-size:14px;font-weight:700}
.week-report-signals{display:flex;flex-wrap:wrap;gap:6px}
.week-report-signal{font-size:11px;color:var(--policy)}
.week-report-signal b{font-family:var(--mono);font-size:10px;margin-right:2px}
.no-report{margin-top:14px;text-align:center;font-size:12px;color:var(--m);padding:10px}
.cta{margin:24px;padding:20px;background:var(--a);border-radius:12px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.cta h3{font-family:var(--serif);font-size:16px;color:#fff}
.cta p{font-size:11px;color:rgba(255,255,255,.6)}
.cta a{padding:11px 20px;background:#fff;color:var(--a);border-radius:8px;font-weight:700;font-size:13px;text-decoration:none;white-space:nowrap}
.bnav{display:none;position:fixed;bottom:0;left:0;right:0;z-index:50;height:58px;background:#fff;border-top:2px solid var(--b);grid-template-columns:repeat(4,1fr);align-items:center;max-width:960px;margin:0 auto}
.bnav a{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--m);font-size:10px;font-weight:600}
@media(max-width:768px){
.hero-archive{padding:22px 16px 18px}
.hero-archive h1{font-size:22px}
.hero-stat .num{font-size:22px}
.hero-dash{flex-wrap:wrap}
.week-group{margin:0 16px 20px}
.week-label{font-size:16px}
.day-card{padding:14px}
.cta{margin:18px 16px}
body{padding-bottom:62px}
.bnav{display:grid}
}
"""

_JS = """
<script>
function toggleDay(btn){
  var card=btn.closest('.day-card');
  var hidden=card.querySelectorAll('.day-hidden');
  var isExp=hidden[0]&&hidden[0].style.display==='block';
  hidden.forEach(function(el){el.style.display=isExp?'none':'block'});
  if(isExp){btn.textContent=btn.getAttribute('data-orig');card.scrollIntoView({behavior:'smooth',block:'start'})}
  else{if(!btn.getAttribute('data-orig'))btn.setAttribute('data-orig',btn.textContent);btn.textContent='접기'}
}
function toggleWeek(btn){
  var group=btn.closest('.week-group');
  var hidden=group.querySelector('.week-hidden');
  if(!hidden)return;
  var isExp=hidden.style.display==='block';
  hidden.style.display=isExp?'none':'block';
  if(isExp){btn.textContent=btn.getAttribute('data-orig');group.scrollIntoView({behavior:'smooth',block:'start'})}
  else{if(!btn.getAttribute('data-orig'))btn.setAttribute('data-orig',btn.textContent);btn.textContent='접기'}
}
</script>
"""


def _iso_week_group(date_str: str) -> tuple[int, int]:
    """날짜 -> (year, iso_week) 반환"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    iso = dt.isocalendar()
    return iso[0], iso[1]


def _week_label(year: int, week: int) -> tuple[str, str, str]:
    """주차 -> ('4월 2주차', '04.07', '04.09') 반환"""
    # ISO week의 월요일
    mon = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w")
    if mon.year < year:
        mon = datetime(year, 1, 1)
    sun = mon + timedelta(days=6)
    month = mon.month
    # 해당 월의 몇 주차인지
    week_of_month = (mon.day - 1) // 7 + 1
    label = f"{month}월 {week_of_month}주차"
    return label, mon.strftime("%m.%d"), sun.strftime("%m.%d")


def _imp_class(impact: str) -> str:
    if impact == "상":
        return "day-imp day-imp-h"
    elif impact == "중":
        return "day-imp day-imp-m"
    return "day-imp day-imp-l"


def _find_weekly_signals(week_dates: list[str]) -> tuple[str, list[str]] | None:
    """주간 시그널 파일이 있는지 확인. (url, signals) 반환"""
    for d in week_dates:
        dt = datetime.strptime(d, "%Y-%m-%d")
        # weekly 파일은 토요일 날짜로 생성됨 — 해당 주의 토요일 찾기
        sat = dt + timedelta(days=(5 - dt.weekday()) % 7)
        weekly_path = ARTICLES_DIR / "weekly" / sat.strftime("%Y-%m-%d") / "index.html"
        if weekly_path.exists():
            # 시그널 제목 추출
            import re
            text = weekly_path.read_text(encoding="utf-8")
            signals = re.findall(r'<h3>([^<]+)</h3>', text)[:5]
            return f"/articles/weekly/{sat.strftime('%Y-%m-%d')}/", signals
    return None


def generate_articles_index():
    """articles/index.html — 주간 그룹핑 + 더보기 + 주간 시그널"""
    json_files = sorted(
        [f for f in DATA_DIR.iterdir() if f.name.startswith("2026-") and f.suffix == ".json"
         and "weekly" not in f.name and "schedule" not in f.name and "subsidies" not in f.name
         and "latest" not in f.name],
        reverse=True,
    )

    # 날짜별 데이터 수집
    days = []
    total_articles = 0
    all_sources = set()
    for jf in json_files[:30]:
        try:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("items", data) if isinstance(data, dict) else data
            if not items:
                continue
            d = jf.stem
            dt = datetime.strptime(d, "%Y-%m-%d")
            dow = _WEEKDAYS[dt.weekday()]
            iso_year, iso_week = dt.isocalendar()[:2]

            cats: dict[str, int] = {}
            for it in items:
                c = it.get("category", "기타")
                cats[c] = cats.get(c, 0) + 1
                src = it.get("source", "")
                if src:
                    all_sources.add(src)

            # 전체 아이템
            all_items = []
            for idx, it in enumerate(items):
                slug = it.get("slug") or f"{idx:03d}"
                detail_exists = (ARTICLES_DIR / d / slug / "detail.html").exists()
                article_exists = (ARTICLES_DIR / d / slug / "index.html").exists()
                link = f"/articles/{d}/{slug}/detail.html" if detail_exists else (
                    f"/articles/{d}/{slug}/" if article_exists else it.get("url", "")
                )
                all_items.append({
                    "title": it.get("title", "")[:70],
                    "source": it.get("source", ""),
                    "impact": it.get("impact", "중"),
                    "link": link,
                })

            total_articles += len(items)
            days.append({
                "date": d, "dow": dow, "count": len(items),
                "cats": cats, "items": all_items,
                "iso_year": iso_year, "iso_week": iso_week,
            })
        except Exception:
            continue

    # 주간 그룹핑
    weeks: dict[tuple[int, int], list[dict]] = {}
    for day in days:
        key = (day["iso_year"], day["iso_week"])
        weeks.setdefault(key, []).append(day)

    # HTML 생성
    week_blocks = []
    for (iso_year, iso_week), week_days in sorted(weeks.items(), reverse=True):
        week_days.sort(key=lambda x: x["date"], reverse=True)
        week_count = sum(d["count"] for d in week_days)
        first_date = week_days[-1]["date"]
        last_date = week_days[0]["date"]
        month = int(last_date.split("-")[1])
        week_of_month = (int(last_date.split("-")[2]) - 1) // 7 + 1
        label = f"{month}월 {week_of_month}주차"
        range_str = f"({first_date[5:].replace('-', '.')} ~ {last_date[5:].replace('-', '.')})"

        # 일별 카드
        day_cards_html = []
        for day in week_days:
            cat_tags = " / ".join(
                f"{c} {n}건" for c, n in sorted(day["cats"].items(), key=lambda x: -x[1])[:4]
            )
            # 기본 5건 표시, 나머지 숨김
            SHOW = 5
            items_html = []
            for i, it in enumerate(day["items"]):
                hidden_cls = " day-hidden" if i >= SHOW else ""
                imp_cls = _imp_class(it["impact"])
                src_short = h.escape(it["source"][:3])
                title = h.escape(it["title"])
                link = h.escape(it["link"], quote=True)
                items_html.append(
                    f'<a class="day-item{hidden_cls}" href="{link}">'
                    f'<span class="{imp_cls}">{h.escape(it["impact"])}</span>'
                    f'<span class="day-src">{src_short} --</span>{title}</a>'
                )

            more_btn = ""
            remaining = len(day["items"]) - SHOW
            if remaining > 0:
                more_btn = f'<button class="day-more" onclick="toggleDay(this)">더보기 ({remaining}건 더)</button>'

            day_cards_html.append(f"""  <div class="day-card">
    <div class="day-head">
      <div><span class="day-date">{day["date"]}</span><span class="day-dow">({day["dow"]})</span></div>
      <span class="day-count">{day["count"]}건</span>
    </div>
    <div class="day-cats">{h.escape(cat_tags)}</div>
    {"".join(items_html)}
    {more_btn}
  </div>""")

        # 주간 시그널 연결
        week_dates = [d["date"] for d in week_days]
        signal_info = _find_weekly_signals(week_dates)
        if signal_info:
            url, signals = signal_info
            sig_spans = "".join(
                f'<span class="week-report-signal"><b>{str(i+1).zfill(2)}</b> {h.escape(s)}</span>'
                for i, s in enumerate(signals)
            )
            report_html = f"""  <a class="week-report" href="{url}">
    <div class="week-report-head">
      <span class="week-report-badge">WEEKLY SIGNAL</span>
      <span class="week-report-title">{label} 주간 정책 시그널</span>
      <span class="week-report-arrow">&#8594;</span>
    </div>
    <div class="week-report-signals">{sig_spans}</div>
  </a>"""
        else:
            report_html = '  <div class="no-report">주간 리포트 준비 중</div>'

        # 일별 카드: 기본 2개 표시, 나머지 숨김
        WEEK_SHOW = 2
        visible_cards = day_cards_html[:WEEK_SHOW]
        hidden_cards = day_cards_html[WEEK_SHOW:]

        hidden_html = ""
        week_more_btn = ""
        if hidden_cards:
            hidden_count = sum(d["count"] for d in week_days[WEEK_SHOW:])
            hidden_days = len(hidden_cards)
            hidden_html = f'<div class="week-hidden">{"".join(hidden_cards)}</div>'
            week_more_btn = f'<button class="week-more" onclick="toggleWeek(this)">{hidden_days}일 더보기 ({hidden_count}건)</button>'

        # 주간 전체 목록 페이지 경로
        week_slug = f"{first_date}--{last_date}"
        week_detail_url = f"/articles/week/{week_slug}/"

        week_blocks.append(f"""<div class="week-group">
  <div class="week-header">
    <div>
      <span class="week-label">{label}</span>
      <span class="week-range">{range_str}</span>
    </div>
    <div>
      <span class="week-total">{week_count}건</span>
      <a class="week-total-link" href="{week_detail_url}">더보기 &#8594;</a>
    </div>
  </div>
{"".join(visible_cards)}
{hidden_html}
{week_more_btn}
{report_html}
</div>""")

    nav_html = render_top_nav("archive")
    footer_html = render_footer()
    num_days = len(days)

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>보도자료 아카이브 - 브리핑룸</title>
<meta name="description" content="51개 부처 보도자료를 주간 단위로 아카이브합니다. AI 요약과 쉬운 설명을 함께 제공합니다.">
<link rel="canonical" href="https://govbrief.kr/articles/">
<meta property="og:title" content="보도자료 아카이브 - 브리핑룸">
<meta property="og:description" content="51개 부처 보도자료를 주간 단위로 아카이브합니다.">
<meta property="og:url" content="https://govbrief.kr/articles/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="govbrief.kr">
<meta property="og:locale" content="ko_KR">
<meta property="og:image" content="https://govbrief.kr/og-image.png">
<meta name="twitter:card" content="summary_large_image">
{SITE_FONT_LINKS}
<style>
{SITE_BASE_CSS}
{SITE_NAV_CSS}
{_PAGE_CSS}
</style>
</head>
<body>

{nav_html}

<section class="hero-archive">
  <div class="hero-top">
    <h1>보도자료 아카이브</h1>
    <div class="hero-sub">51개 부처 보도자료 날짜별 브리핑</div>
  </div>
  <div class="hero-dash">
    <div class="hero-stat"><div class="num">{total_articles:,}</div><div class="label">총 보도자료</div></div>
    <div class="hero-stat"><div class="num">{len(all_sources)}</div><div class="label">참여 부처</div></div>
    <div class="hero-stat"><div class="num">{num_days}일</div><div class="label">수록 기간</div></div>
  </div>
  <div class="sbox">
    <span class="si">&#x2315;</span>
    <input id="archive-search" placeholder="보도자료 제목, 부처명 검색..." autocomplete="off">
  </div>
</section>

{"".join(week_blocks)}

<div class="cta">
  <div><h3>매일 3분 브리핑</h3><p>텔레그램에서 받아보세요</p></div>
  <a href="https://t.me/govbrief" target="_blank" rel="noopener">구독</a>
</div>

{footer_html}
<nav class="bnav"><a href="/"><span style="font-size:14px;font-weight:700">H</span>홈</a><a href="/policy/"><span style="font-size:14px;font-weight:700">P</span>정책</a><a href="/finlaw/"><span style="font-size:14px;font-weight:700">L</span>법령</a><a href="/articles/"><span style="font-size:14px;font-weight:700">A</span>기록</a></nav>

{_JS}
</body>
</html>"""

    out = ARTICLES_DIR / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"[articles_gen] index.html 생성 -- {num_days}일, {total_articles}건, {len(weeks)}주")

    # ── 주간 전체 목록 페이지 생성 ──
    _generate_week_detail_pages(weeks, nav_html, footer_html)

    return num_days


def _generate_week_detail_pages(
    weeks: dict[tuple[int, int], list[dict]],
    nav_html: str,
    footer_html: str,
):
    """각 주간 전체 보도자료 목록 페이지 생성"""

    detail_css = """
.hero-week{background:#fff8f3;padding:28px 24px 22px;border-bottom:1px solid var(--ab)}
.hero-back{font-size:12px;color:var(--a);text-decoration:none;font-weight:600;display:inline-block;margin-bottom:12px}
.hero-week .hero-top{text-align:center;margin-bottom:16px}
.hero-week h1{font-family:var(--serif);font-size:26px;font-weight:700;margin-bottom:4px;line-height:1.35}
.hero-range{font-family:var(--mono);font-size:15px;color:var(--t2);margin-bottom:2px}
.hero-week .hero-sub{font-size:13px;color:var(--m)}
.hero-dash{display:flex;gap:10px;margin-bottom:0}
.hero-stat{flex:1;background:var(--s);border:1px solid var(--ab);border-radius:12px;padding:12px;text-align:center}
.hero-stat .num{font-family:var(--mono);font-size:26px;font-weight:700;color:var(--a);line-height:1}
.hero-stat .label{font-size:11px;font-weight:700;color:var(--a);margin-top:4px}
.filter-bar{padding:14px 24px;border-bottom:1px solid var(--bl);display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.filter-tab{padding:6px 14px;border-radius:20px;border:1px solid var(--bl);background:var(--s);font-size:12px;font-weight:600;color:var(--t2);cursor:pointer;white-space:nowrap}
.filter-tab.on{background:var(--a);color:#fff;border-color:var(--a)}
.filter-tab:hover{border-color:var(--a)}
.day-section{padding:0 24px;margin-top:20px}
.day-anchor{font-family:var(--serif);font-size:18px;font-weight:700;padding-bottom:8px;border-bottom:2px solid var(--a);display:flex;align-items:center;justify-content:space-between}
.day-anchor-count{font-family:var(--mono);font-size:13px;color:var(--a);font-weight:700}
.day-anchor-dow{font-size:13px;color:var(--m);font-weight:400;margin-left:6px}
.item{display:flex;align-items:flex-start;gap:10px;padding:12px 0;border-bottom:1px dashed var(--bl);text-decoration:none;color:var(--t)}
.item:last-child{border-bottom:none}
.item:hover{background:var(--al);margin:0 -8px;padding:12px 8px;border-radius:6px}
.item-imp{font-family:var(--mono);font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;white-space:nowrap;flex-shrink:0;margin-top:2px}
.item-imp-h{background:#fee2e2;color:#dc2626}
.item-imp-m{background:#fef3c7;color:#d97706}
.item-imp-l{background:#f3f4f6;color:#6b7280}
.item-body{flex:1;min-width:0}
.item-title{font-size:14px;font-weight:600;line-height:1.5;margin-bottom:2px}
.item-meta{font-size:11px;color:var(--m)}
.item-cat{font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px;margin-left:6px}
.item-cat-fin{background:#dbeafe;color:#1d4ed8}
.item-cat-ind{background:#fef3c7;color:#92400e}
.item-cat-soc{background:#d1fae5;color:#065f46}
.item-cat-dip{background:#ede9fe;color:#5b21b6}
.item-cat-adm{background:#f3f4f6;color:#374151}
.divider-sm{height:1px;background:var(--bl);margin:20px 24px 0}
.cta{margin:24px;padding:20px;background:var(--a);border-radius:12px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.cta h3{font-family:var(--serif);font-size:16px;color:#fff}
.cta p{font-size:11px;color:rgba(255,255,255,.6)}
.cta a{padding:11px 20px;background:#fff;color:var(--a);border-radius:8px;font-weight:700;font-size:13px;text-decoration:none;white-space:nowrap}
.bnav{display:none;position:fixed;bottom:0;left:0;right:0;z-index:50;height:58px;background:#fff;border-top:2px solid var(--b);grid-template-columns:repeat(4,1fr);align-items:center;max-width:960px;margin:0 auto}
.bnav a{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--m);font-size:10px;font-weight:600}
@media(max-width:768px){
.hero-week{padding:18px 16px}
.hero-week h1{font-size:20px}
.hero-stat .num{font-size:20px}
.hero-dash{flex-wrap:wrap}
.filter-bar{padding:10px 16px}
.day-section{padding:0 16px}
.cta{margin:18px 16px}
body{padding-bottom:62px}
.bnav{display:grid}
}
"""

    _CAT_CLS = {
        "금융경제": "item-cat-fin",
        "산업기술": "item-cat-ind",
        "사회복지": "item-cat-soc",
        "외교안보": "item-cat-dip",
        "행정법제": "item-cat-adm",
    }

    filter_js = """
<script>
document.querySelectorAll('.filter-tab').forEach(function(tab){
  tab.addEventListener('click',function(){
    document.querySelectorAll('.filter-tab').forEach(function(t){t.classList.remove('on')});
    tab.classList.add('on');
    var cat=tab.getAttribute('data-cat');
    document.querySelectorAll('.item').forEach(function(item){
      item.style.display=(cat==='all'||item.getAttribute('data-cat')===cat)?'flex':'none';
    });
  });
});
</script>
"""

    for (iso_year, iso_week), week_days in weeks.items():
        week_days_sorted = sorted(week_days, key=lambda x: x["date"], reverse=True)
        first_date = week_days_sorted[-1]["date"]
        last_date = week_days_sorted[0]["date"]
        week_slug = f"{first_date}--{last_date}"
        week_count = sum(d["count"] for d in week_days_sorted)
        num_sources = len(set(
            it["source"] for d in week_days_sorted for it in d["items"] if it.get("source")
        ))
        num_high = sum(
            1 for d in week_days_sorted for it in d["items"] if it.get("impact") == "상"
        )

        month = int(last_date.split("-")[1])
        week_of_month = (int(last_date.split("-")[2]) - 1) // 7 + 1
        label = f"{month}월 {week_of_month}주차"

        # 분야별 집계
        all_cats: dict[str, int] = {}
        for d in week_days_sorted:
            for c, n in d["cats"].items():
                all_cats[c] = all_cats.get(c, 0) + n

        # 필터 탭
        filter_tabs = [f'<span class="filter-tab on" data-cat="all">전체 {week_count}</span>']
        for cat, cnt in sorted(all_cats.items(), key=lambda x: -x[1]):
            filter_tabs.append(f'<span class="filter-tab" data-cat="{h.escape(cat)}">{h.escape(cat)} {cnt}</span>')

        # 일별 섹션
        day_sections = []
        for i, day in enumerate(week_days_sorted):
            items_html = []
            for it in day["items"]:
                imp = it.get("impact", "중")
                imp_cls = "item-imp-h" if imp == "상" else ("item-imp-m" if imp == "중" else "item-imp-l")
                cat = ""
                # 카테고리 찾기
                for c in day["cats"]:
                    cat = c
                    break
                # 아이템별 카테고리는 원본 데이터에서
                item_cat = ""
                cat_cls = ""
                src = it.get("source", "")
                # 원본 JSON에서 카테고리 매핑 (source 기반 추정)
                for c_name in all_cats:
                    cat_cls = _CAT_CLS.get(c_name, "item-cat-adm")

                link = h.escape(it["link"], quote=True)
                items_html.append(f"""  <a class="item" href="{link}" data-cat="all" data-imp="{h.escape(imp)}">
    <span class="item-imp {imp_cls}">{h.escape(imp)}</span>
    <div class="item-body">
      <div class="item-title">{h.escape(it["title"])}</div>
      <div class="item-meta">{h.escape(src)}</div>
    </div>
  </a>""")

            divider = '<div class="divider-sm"></div>' if i > 0 else ''
            day_sections.append(f"""{divider}
<div class="day-section">
  <div class="day-anchor">
    <span>{day["date"]}<span class="day-anchor-dow">({day["dow"]})</span></span>
    <span class="day-anchor-count">{day["count"]}건</span>
  </div>
{"".join(items_html)}
</div>""")

        detail_page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{label} 보도자료 ({week_count}건) - 브리핑룸</title>
<meta name="description" content="{label} 정부 보도자료 전체 목록 ({week_count}건)">
{SITE_FONT_LINKS}
<style>
{SITE_BASE_CSS}
{SITE_NAV_CSS}
{detail_css}
</style>
</head>
<body>

{nav_html}

<section class="hero-week">
  <a class="hero-back" href="/articles/">&larr; 아카이브로 돌아가기</a>
  <div class="hero-top">
    <h1>{label} 보도자료</h1>
    <div class="hero-range">{first_date} ~ {last_date}</div>
    <div class="hero-sub">51개 부처 보도자료 주간 전체 목록</div>
  </div>
  <div class="hero-dash">
    <div class="hero-stat"><div class="num">{week_count}</div><div class="label">총 보도자료</div></div>
    <div class="hero-stat"><div class="num">{num_sources}</div><div class="label">참여 부처</div></div>
    <div class="hero-stat"><div class="num">{len(week_days_sorted)}</div><div class="label">수록일</div></div>
    <div class="hero-stat"><div class="num">{num_high}</div><div class="label">영향도 상</div></div>
  </div>
</section>

<div class="filter-bar">
  {"".join(filter_tabs)}
</div>

{"".join(day_sections)}

<div class="cta">
  <div><h3>매일 3분 브리핑</h3><p>텔레그램에서 받아보세요</p></div>
  <a href="https://t.me/govbrief" target="_blank" rel="noopener">구독</a>
</div>

{footer_html}
<nav class="bnav"><a href="/"><span style="font-size:14px;font-weight:700">H</span>홈</a><a href="/policy/"><span style="font-size:14px;font-weight:700">P</span>정책</a><a href="/finlaw/"><span style="font-size:14px;font-weight:700">L</span>법령</a><a href="/articles/"><span style="font-size:14px;font-weight:700">A</span>기록</a></nav>

{filter_js}
</body>
</html>"""

        out_dir = ARTICLES_DIR / "week" / week_slug
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "index.html"
        out_path.write_text(detail_page, encoding="utf-8")
        print(f"  [week-detail] {week_slug} -- {week_count}건")


def main():
    generate_articles_index()


if __name__ == "__main__":
    main()
