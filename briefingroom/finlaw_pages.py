"""finlaw 정적 페이지 재생성

finance_law.db에서 데이터를 읽어 finlaw/cases/index.html, finlaw/notices/index.html을 재생성합니다.
개정이유(amendment_reason), 판례요지(summary) 포함.

실행: python -m briefingroom.finlaw_pages
"""
from __future__ import annotations

import html
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from briefingroom.site_templates import SITE_NAV_CSS, render_bottom_nav, render_top_nav, render_footer

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"
FINLAW_DIR = BASE_DIR / "finlaw"

# CSS는 별도 파일로 관리하지 않고 인라인
# finlaw/index.html의 <style> 블록을 읽어서 재사용
_FINLAW_CSS_FILE = FINLAW_DIR / "index.html"

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

# 법령 카테고리 요약 (정적)
_LAW_CATEGORIES = [
    ("금융감독 기본법", "3건", "금융소비자보호법, 금융위설치법 등"),
    ("은행", "10건", "은행법, 예금자보호법, 한국은행법 등"),
    ("자본시장 / 증권", "5건", "자본시장법, 증권거래세법 등"),
    ("보험", "2건", "보험업법, 보험사기방지특별법"),
    ("여신 / 신용", "7건", "여신전문금융업법, 신용정보법 등"),
    ("전자금융 / 핀테크", "3건", "전자금융거래법, 가상자산법 등"),
    ("개인정보 / 정보보호", "4건", "개인정보보호법, 정보통신망법 등"),
    ("금융지주 / 지배구조", "2건", "금융지주회사법, 지배구조법"),
    ("외환", "1건", "외국환거래법"),
    ("자금세탁방지", "1건", "특정금융거래정보법"),
    ("정책금융", "3건", "한국주택금융공사법 등"),
    ("기타 금융", "12건", "금융실명거래법, 금융혁신지원법 등"),
]


def _clean_html(text: str) -> str:
    """HTML 태그 제거 + 정리"""
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200]


def _brief_text(text: str, fallback: str, limit: int = 110) -> str:
    value = (text or "").strip()
    if not value or value == "-":
        value = fallback
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= limit:
        return value
    cut = value.rfind(" ", 0, limit)
    if cut < 40:
        cut = limit
    return value[:cut].rstrip(" ,.") + "…"


def generate_cases_page():
    """판례 페이지 재생성 — summary 컬럼 포함"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT prec_id, case_name, case_number, court, decision_date, "
            "summary, detail_link FROM precedents ORDER BY decision_date DESC"
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        print("[finlaw_pages] precedents 테이블 없음 → cases 페이지 스킵")
        return
    conn.close()

    tbody = []
    for r in rows:
        date = r["decision_date"] or ""
        court = r["court"] or ""
        prec_id = r["prec_id"] or ""
        name = html.escape(r["case_name"] or "")
        number = html.escape(r["case_number"] or "")
        summary = _clean_html(r["summary"] or "")
        link = html.escape(r["detail_link"] or "", quote=True)

        summary_html = ""
        if summary and summary != "-":
            summary_html = f'<div style="font-size:11px;color:var(--t2);margin-top:4px;line-height:1.5">{html.escape(summary[:100])}</div>'

        # 상세 페이지 존재 여부
        detail_link = f"/finlaw/cases/{prec_id}/" if (FINLAW_DIR / "cases" / prec_id / "index.html").exists() else ""
        title_html = f'<a href="{detail_link}" style="text-decoration:none;color:var(--t);font-weight:600">{name}</a>' if detail_link else f'<div style="font-weight:600">{name}</div>'

        tbody.append(f"""<tr>
      <td>{date}</td>
      <td>{html.escape(court)}</td>
      <td>{title_html}<div style="font-size:11px;color:var(--m);margin-top:2px">{number}</div>{summary_html}</td>
      <td><a href="{link}" target="_blank" rel="noopener" style="color:var(--a);text-decoration:none;font-size:11px">원문 →</a></td>
    </tr>""")

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>금융 판례 - 브리핑룸</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace;--law:#047857;--law-bg:#ecfdf5;--law-border:#a7f3d0}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--t);font-family:var(--sans);max-width:960px;margin:0 auto;padding:58px 0 0}}
.hdr{{position:fixed;top:0;left:0;right:0;z-index:50;max-width:960px;margin:0 auto;background:#f5f5f5;border-bottom:3px solid var(--a);height:54px;display:flex;align-items:center;padding:0 20px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.logo{{font-family:var(--serif);font-size:19px;font-weight:700;color:var(--t);text-decoration:none;margin-right:16px;white-space:nowrap}}
.hnav{{display:flex;gap:0;align-items:center;flex:1;min-width:0}}
.hnav a{{font-size:14px;font-weight:600;color:var(--m);text-decoration:none;padding:6px 12px;border-radius:5px;white-space:nowrap}}
.hnav a.on{{color:var(--a);background:var(--al);font-weight:700}}
.bell{{color:var(--m);text-decoration:none;font-size:14px;font-weight:600;margin-left:auto;flex-shrink:0}}
.wrap{{padding:24px 20px 80px}}
.back{{color:var(--m);text-decoration:none;font-size:13px;display:inline-block;margin-bottom:16px}}
h1{{font-family:var(--serif);font-size:26px;margin-bottom:8px}}
.desc{{color:var(--t2);font-size:14px;margin-bottom:16px}}
.nav{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
.nav a{{padding:8px 16px;border-radius:8px;border:1px solid var(--b);background:var(--s);font-size:13px;font-weight:600;color:var(--t);text-decoration:none}}
.nav a:hover{{border-color:var(--a)}}
.nav a.active{{background:var(--a);color:#fff;border-color:var(--a)}}
.filter-bar{{display:flex;gap:8px;align-items:center;margin-bottom:16px;flex-wrap:wrap}}
.filter-bar label{{font-size:12px;color:var(--t2);font-weight:600}}
.filter-bar input[type=date]{{font-family:var(--mono);font-size:12px;padding:6px 10px;border:1px solid var(--b);border-radius:6px;background:var(--s);color:var(--t);outline:none}}
.filter-bar input[type=date]:focus{{border-color:var(--a)}}
.filter-bar button{{padding:6px 14px;border-radius:6px;border:1px solid var(--a);background:var(--a);color:#fff;font-size:12px;font-weight:600;cursor:pointer;font-family:var(--sans)}}
table{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px;background:var(--s);border:1px solid var(--b);border-radius:10px;overflow:hidden}}
col.c-date{{width:90px}}
col.c-court{{width:60px}}
col.c-case{{width:auto}}
col.c-link{{width:52px}}
th{{background:var(--a);color:#fff;padding:10px 8px;text-align:left;font-size:12px;white-space:nowrap}}
td{{padding:10px 8px;border-bottom:1px solid var(--b);vertical-align:top}}
td:first-child{{white-space:nowrap;font-family:var(--mono);font-size:11px;color:var(--t2)}}
td:nth-child(2){{white-space:nowrap;font-size:12px}}
td:nth-child(4){{white-space:nowrap;text-align:center}}
td:nth-child(3) div:first-child{{word-break:keep-all;overflow-wrap:break-word}}
tr:last-child td{{border-bottom:none}}
@media(max-width:768px){{
  body{{padding-top:52px}}
  .hdr{{height:50px;padding:0 14px}}
  .logo{{font-size:17px;margin-right:10px}}
  .hnav a{{font-size:11px;padding:5px 8px}}
  table{{font-size:11px}}
  td,th{{padding:8px 6px}}
}}
</style>
</head>
<body>
{render_top_nav("finlaw")}
<div class="wrap">
<a class="back" href="/finlaw/">← 금융 법령 AI</a>
<h1>금융 판례</h1>
<div class="desc">금융 관련 대법원/고등법원 판례 {len(rows)}건</div>
<div class="nav">
  <a href="/finlaw/">법령 목록</a>
  <a class="active" href="/finlaw/cases/">판례 {len(rows)}건</a>
  <a href="/finlaw/notices/">법령 개정 이력</a>
</div>
<div style="position:relative;margin-bottom:12px">
  <span style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--m);font-size:14px">⌕</span>
  <input id="case-search" type="text" placeholder="사건명, 사건번호, 법원으로 검색..." style="width:100%;padding:12px 14px 12px 36px;font-size:14px;border:2px solid var(--b);border-radius:10px;background:var(--s);color:var(--t);outline:none;font-family:var(--sans)">
</div>
<div class="filter-bar">
  <label>기간</label>
  <input type="date" id="date-from" value="2025-01-01"> <span style="color:var(--m)">~</span> <input type="date" id="date-to" value="2026-04-01">
  <button onclick="filterByDate()">조회</button>
  <span id="result-count" style="font-family:var(--mono);font-size:11px;color:var(--m);margin-left:8px"></span>
</div>
<table>
<colgroup><col class="c-date"><col class="c-court"><col class="c-case"><col class="c-link"></colgroup>
<thead><tr><th>선고일</th><th>법원</th><th>사건명 / 사건번호</th><th>원문</th></tr></thead>
<tbody>{"".join(tbody)}</tbody>
</table>
</div>
<script>
const rows = document.querySelectorAll('table tbody tr');
const searchInput = document.getElementById('case-search');
const countEl = document.getElementById('result-count');
function updateCount() {{
  const visible = document.querySelectorAll('table tbody tr:not([style*="display: none"])').length;
  countEl.textContent = visible + '건 표시';
}}
searchInput.addEventListener('input', function() {{
  const val = this.value.trim().toLowerCase();
  if (!val) {{ rows.forEach(r => r.style.display = ''); updateCount(); return; }}
  const terms = val.split(/\\s+/);
  rows.forEach(r => {{
    const text = r.textContent.toLowerCase();
    const match = terms.every(t => text.includes(t));
    r.style.display = match ? '' : 'none';
  }});
  updateCount();
}});
function filterByDate() {{
  const from = document.getElementById('date-from').value.replace(/-/g, '.');
  const to = document.getElementById('date-to').value.replace(/-/g, '.');
  rows.forEach(r => {{
    const dateCell = r.cells[0].textContent.trim();
    r.style.display = (dateCell >= from && dateCell <= to) ? '' : 'none';
  }});
  updateCount();
}}
updateCount();
</script>
</body>
</html>"""

    out = FINLAW_DIR / "cases" / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"[finlaw_pages] cases/index.html 생성 — {len(rows)}건")


def generate_notices_page():
    """법령 개정 이력 페이지 재생성 — amendment_reason 포함"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT name, promulgation_date, revision_type, ministry, "
            "detail_link, amendment_reason FROM laws "
            "WHERE promulgation_date >= '20250101' "
            "ORDER BY promulgation_date DESC"
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        print("[finlaw_pages] laws 테이블 없음 → notices 페이지 스킵")
        return
    conn.close()

    tbody = []
    for r in rows:
        date = r["promulgation_date"] or ""
        if len(date) == 8:
            date = f"{date[:4]}.{date[4:6]}.{date[6:]}"
        rev_type = r["revision_type"] or ""
        name = html.escape(r["name"] or "")
        ministry = html.escape(r["ministry"] or "")
        link = html.escape(r["detail_link"] or "", quote=True)
        reason = _clean_html(r["amendment_reason"] or "")

        # 태그 색상
        tag_cls = "edit"
        if "제정" in rev_type:
            tag_cls = "new"

        reason_html = ""
        if reason and reason != "-":
            reason_html = f'<div style="font-size:11px;color:var(--t2);margin-top:4px;line-height:1.5">{html.escape(reason)}</div>'

        full_link = f"https://www.law.go.kr/DRF/lawService.do?OC=sony0125&target=law&MST={r['detail_link'] if r['detail_link'] and r['detail_link'].isdigit() else ''}&type=HTML&mobileYn="
        if link and not link.startswith("http"):
            full_link = f"https://www.law.go.kr{link}"
        elif link.startswith("http"):
            full_link = link

        tbody.append(f"""<tr>
      <td>{date}</td>
      <td><span style="font-size:10px;padding:2px 6px;border-radius:3px;background:#eef2ff;color:#3730a3">{html.escape(rev_type)}</span></td>
      <td><div style="font-weight:600">{name}</div><div style="font-size:11px;color:var(--m);margin-top:2px">{ministry}</div>{reason_html}</td>
      <td><a href="{full_link}" target="_blank" rel="noopener" style="color:var(--a);text-decoration:none;font-size:11px">전문 →</a></td>
    </tr>""")

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>법령 개정 이력 - 브리핑룸</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace;--law:#047857;--law-bg:#ecfdf5;--law-border:#a7f3d0}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--t);font-family:var(--sans);max-width:960px;margin:0 auto;padding:58px 0 0}}
.hdr{{position:fixed;top:0;left:0;right:0;z-index:50;max-width:960px;margin:0 auto;background:#f5f5f5;border-bottom:3px solid var(--a);height:54px;display:flex;align-items:center;padding:0 20px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.logo{{font-family:var(--serif);font-size:19px;font-weight:700;color:var(--t);text-decoration:none;margin-right:16px;white-space:nowrap}}
.hnav{{display:flex;gap:0;align-items:center;flex:1;min-width:0}}
.hnav a{{font-size:14px;font-weight:600;color:var(--m);text-decoration:none;padding:6px 12px;border-radius:5px;white-space:nowrap}}
.hnav a.on{{color:var(--a);background:var(--al);font-weight:700}}
.bell{{color:var(--m);text-decoration:none;font-size:14px;font-weight:600;margin-left:auto;flex-shrink:0}}
.wrap{{padding:24px 20px 80px}}
.back{{color:var(--m);text-decoration:none;font-size:13px;display:inline-block;margin-bottom:16px}}
h1{{font-family:var(--serif);font-size:26px;margin-bottom:8px}}
.desc{{color:var(--t2);font-size:14px;margin-bottom:16px}}
.nav{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
.nav a{{padding:8px 16px;border-radius:8px;border:1px solid var(--b);background:var(--s);font-size:13px;font-weight:600;color:var(--t);text-decoration:none}}
.nav a:hover{{border-color:var(--a)}}
.nav a.active{{background:var(--a);color:#fff;border-color:var(--a)}}
.filter-bar{{display:flex;gap:8px;align-items:center;margin-bottom:16px;flex-wrap:wrap}}
.filter-bar label{{font-size:12px;color:var(--t2);font-weight:600}}
.filter-bar input[type=date]{{font-family:var(--mono);font-size:12px;padding:6px 10px;border:1px solid var(--b);border-radius:6px;background:var(--s);color:var(--t);outline:none}}
.filter-bar input[type=date]:focus{{border-color:var(--a)}}
.filter-bar button{{padding:6px 14px;border-radius:6px;border:1px solid var(--a);background:var(--a);color:#fff;font-size:12px;font-weight:600;cursor:pointer;font-family:var(--sans)}}
table{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px;background:var(--s);border:1px solid var(--b);border-radius:10px;overflow:hidden}}
col.c-date{{width:90px}}
col.c-type{{width:70px}}
col.c-name{{width:auto}}
col.c-link{{width:52px}}
th{{background:var(--a);color:#fff;padding:10px 8px;text-align:left;font-size:12px;white-space:nowrap}}
td{{padding:10px 8px;border-bottom:1px solid var(--b);vertical-align:top}}
td:first-child{{white-space:nowrap;font-family:var(--mono);font-size:11px;color:var(--t2)}}
td:nth-child(2){{white-space:nowrap;text-align:center}}
td:nth-child(4){{white-space:nowrap;text-align:center}}
tr:last-child td{{border-bottom:none}}
@media(max-width:768px){{
  body{{padding-top:52px}}
  .hdr{{height:50px;padding:0 14px}}
  .logo{{font-size:17px;margin-right:10px}}
  .hnav a{{font-size:11px;padding:5px 8px}}
  table{{font-size:11px}}
  td,th{{padding:8px 6px}}
}}
</style>
</head>
<body>
{render_top_nav("finlaw")}
<div class="wrap">
<a class="back" href="/finlaw/">← 금융 법령 AI</a>
<h1>법령 개정 이력</h1>
<div class="desc">2025년 이후 공포/개정된 금융 법령 {len(rows)}건</div>
<div class="nav">
  <a href="/finlaw/">법령 목록</a>
  <a href="/finlaw/cases/">판례</a>
  <a class="active" href="/finlaw/notices/">법령 개정 이력</a>
</div>
<div style="position:relative;margin-bottom:12px">
  <span style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--m);font-size:14px">⌕</span>
  <input id="law-search" type="text" placeholder="법령명, 소관부처로 검색..." style="width:100%;padding:12px 14px 12px 36px;font-size:14px;border:2px solid var(--b);border-radius:10px;background:var(--s);color:var(--t);outline:none;font-family:var(--sans)">
</div>
<div class="filter-bar">
  <label>기간</label>
  <input type="date" id="date-from" value="2025-01-01"> <span style="color:var(--m)">~</span> <input type="date" id="date-to" value="2026-04-01">
  <button onclick="filterByDate()">조회</button>
  <span id="result-count" style="font-family:var(--mono);font-size:11px;color:var(--m);margin-left:8px"></span>
</div>
<table>
<colgroup><col class="c-date"><col class="c-type"><col class="c-name"><col class="c-link"></colgroup>
<thead><tr><th>공포일</th><th>구분</th><th>법령명 / 소관부처</th><th>전문</th></tr></thead>
<tbody>{"".join(tbody)}</tbody>
</table>
</div>
<script>
const rows = document.querySelectorAll('table tbody tr');
const searchInput = document.getElementById('law-search');
const countEl = document.getElementById('result-count');
function updateCount() {{
  const visible = document.querySelectorAll('table tbody tr:not([style*="display: none"])').length;
  countEl.textContent = visible + '건 표시';
}}
searchInput.addEventListener('input', function() {{
  const val = this.value.trim().toLowerCase();
  if (!val) {{ rows.forEach(r => r.style.display = ''); updateCount(); return; }}
  const terms = val.split(/\\s+/);
  rows.forEach(r => {{
    const text = r.textContent.toLowerCase();
    const match = terms.every(t => text.includes(t));
    r.style.display = match ? '' : 'none';
  }});
  updateCount();
}});
function filterByDate() {{
  const from = document.getElementById('date-from').value.replace(/-/g, '.');
  const to = document.getElementById('date-to').value.replace(/-/g, '.');
  rows.forEach(r => {{
    const dateCell = r.cells[0].textContent.trim();
    r.style.display = (dateCell >= from && dateCell <= to) ? '' : 'none';
  }});
  updateCount();
}}
updateCount();
</script>
</body>
</html>"""

    out = FINLAW_DIR / "notices" / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"[finlaw_pages] notices/index.html 생성 — {len(rows)}건")


def generate_finlaw_index():
    """finlaw/index.html 재생성 — DB 기반 동적 데이터"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    today = date.today()
    today_str = today.strftime("%Y%m%d")
    week_ago = (today - timedelta(days=7)).strftime("%Y%m%d")
    today_dot = today.strftime("%Y. %m. %d")
    dow = _WEEKDAYS[today.weekday()]

    # 최근 법령 변경 (30일)
    month_ago = (today - timedelta(days=30)).strftime("%Y%m%d")
    recent_laws = []
    try:
        recent_laws = conn.execute(
            "SELECT name, promulgation_date, revision_type, ministry, amendment_reason, law_mst "
            "FROM laws WHERE promulgation_date >= ? ORDER BY promulgation_date DESC LIMIT 5",
            (month_ago,),
        ).fetchall()
    except sqlite3.OperationalError:
        pass  # 테이블 없으면 무시

    # 최근 판례 (summary 있는 것)
    recent_precs = []
    try:
        recent_precs = conn.execute(
            "SELECT prec_id, case_name, decision_date, court, case_number, summary, related_law "
            "FROM precedents WHERE summary IS NOT NULL AND summary != '' AND summary != '-' "
            "ORDER BY decision_date DESC LIMIT 3",
        ).fetchall()
    except sqlite3.OperationalError:
        pass  # 테이블 없으면 무시

    # 입법예고 (D-day > 0 = 진행 중)
    leg_notices = []
    try:
        leg_notices = conn.execute(
            "SELECT title, department, law_type, period_start, period_end, "
            "days, opinion_count, detail_link FROM leg_notices "
            "WHERE days > 0 ORDER BY days ASC LIMIT 5"
        ).fetchall()
    except sqlite3.OperationalError:
        pass  # 테이블 없으면 무시

    # 카운트
    try:
        law_count = len(conn.execute(
            "SELECT 1 FROM laws WHERE promulgation_date >= ?", (month_ago,)
        ).fetchall())
    except sqlite3.OperationalError:
        law_count = 0
    try:
        prec_count = conn.execute("SELECT COUNT(*) FROM precedents").fetchone()[0]
    except sqlite3.OperationalError:
        prec_count = 0
    notice_count = len(leg_notices)
    try:
        total_laws = conn.execute("SELECT COUNT(*) FROM laws").fetchone()[0]
    except sqlite3.OperationalError:
        total_laws = 0
    conn.close()

    if total_laws <= 0 and (FINLAW_DIR / "detail").exists():
        total_laws = len([p for p in (FINLAW_DIR / "detail").iterdir() if p.is_dir()])
    if prec_count <= 0 and (FINLAW_DIR / "cases").exists():
        prec_count = len([p for p in (FINLAW_DIR / "cases").iterdir() if p.is_dir()])

    # 헤드라인: 가장 최근 법령 변경
    headline_title = ""
    headline_sub = ""
    if recent_laws:
        rl = recent_laws[0]
        headline_title = f"{rl['name']} — {rl['revision_type']}"
        reason = _clean_html(rl["amendment_reason"] or "")
        headline_sub = _brief_text(reason, f"{rl['ministry']} 소관", limit=80)

    # 변경 카드 생성
    change_cards = []
    for r in recent_laws:
        d = r["promulgation_date"]
        if len(d) == 8:
            d = f"{d[:4]}.{d[4:6]}.{d[6:]}"
        reason = _brief_text(_clean_html(r["amendment_reason"] or ""), f"{r['ministry']} 소관 법령 개정")
        mst = r["law_mst"] or ""
        link = f"/finlaw/detail/{mst}/" if mst else "/finlaw/notices/"
        search_text = f"{r['name']} {r['ministry']} {r['revision_type']} {reason}".lower()
        change_cards.append(f"""  <a href="{link}" class="finlaw-searchable" data-type="change" data-search="{html.escape(search_text)}" style="text-decoration:none;color:inherit"><div class="change-card" style="cursor:pointer">
    <div class="change-head">
      <span class="change-tag edit">{html.escape(r['revision_type'])}</span>
      <span class="change-date">{d}</span>
    </div>
    <div class="change-title">{html.escape(r['name'])}</div>
    <div class="change-desc">{html.escape(reason)}</div>
  </div></a>""")

    # 판례 카드 생성
    case_cards = []
    for r in recent_precs:
        summary = _brief_text(_clean_html(r["summary"] or ""), "판결 요지가 준비 중입니다.")
        law = html.escape(r["related_law"] or "")
        law_html = f'<div class="case-laws"><span>{law}</span></div>' if law else ""
        detail_link = f"/finlaw/cases/{r['prec_id']}/" if r["prec_id"] else "/finlaw/cases/"
        search_text = f"{r['case_name']} {r['court'] or ''} {r['case_number'] or ''} {r['related_law'] or ''} {summary}".lower()
        case_cards.append(f"""  <a href="{detail_link}" class="finlaw-searchable" data-type="case" data-search="{html.escape(search_text)}" style="text-decoration:none;color:inherit"><div class="case-card">
    <div class="case-court">{html.escape(r['court'] or '')} · {r['decision_date']} · {html.escape(r['case_number'] or '')}</div>
    <div class="case-title">{html.escape(r['case_name'])}</div>
    <div class="case-summary">{html.escape(summary)}</div>
    {law_html}
  </div></a>""")

    # 입법예고 카드
    notice_cards = []
    for n in leg_notices:
        d = n["days"]
        if d <= 7:
            cls = "soon"
        elif d <= 20:
            cls = "mid"
        else:
            cls = "far"
        detail_link = n["detail_link"] or "/finlaw/notices/"
        search_text = f"{n['title']} {n['department']} {n['law_type'] or ''}".lower()
        notice_cards.append(f"""  <a href="{html.escape(detail_link)}" class="finlaw-searchable" data-type="notice" data-search="{html.escape(search_text)}" style="text-decoration:none;color:inherit"><div class="notice-card">
    <div class="notice-dday {cls}"><span class="d">D-</span><span class="n">{d}</span></div>
    <div class="notice-body">
      <div class="notice-title">{html.escape(n['title'])}</div>
      <div class="notice-meta">{html.escape(n['department'])} · {n['period_start']} ~ {n['period_end']} · 의견 {n['opinion_count']}건</div>
    </div>
  </div></a>""")

    # 법령 DB 카테고리 카드
    db_cards = []
    for name, count, desc in _LAW_CATEGORIES:
        db_cards.append(f'    <div class="fl-card"><div class="fl-name">{name}</div><div class="fl-meta">{count} · {desc}</div></div>')

    # CSS 읽기 (현재 파일에서)
    css = ""
    if _FINLAW_CSS_FILE.exists():
        content = _FINLAW_CSS_FILE.read_text(encoding="utf-8")
        m = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
        if m:
            css = m.group(1)

    dot_class = '<div class="dot"></div>' if law_count > 0 else ""

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>금융 법령 AI - 브리핑룸</title>
<meta name="description" content="한국 금융 법령 {total_laws}건과 최근 판례, 입법예고를 모니터링하고 핵심 변화만 빠르게 확인합니다.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>

{render_top_nav("finlaw")}

<section class="hero" style="background:var(--law-bg);border-bottom:1px solid var(--law-border)">
  <div class="hero-top">
    <h1>금융 법령 AI</h1>
    <div class="hero-date">{today_dot} ({dow})</div>
    <div class="hero-sub">금융 법령 {total_laws}건 · 판례 {prec_count}건 · 매일 모니터링</div>
  </div>

  <div class="hero-dash">
    <div class="hero-stat" style="border-color:var(--law-border)"><div class="num" style="color:var(--law)">{law_count}</div><div class="label" style="color:var(--law)">법령 개정</div></div>
    <div class="hero-stat" style="border-color:var(--law-border)"><div class="num" style="color:var(--law)">{prec_count}</div><div class="label" style="color:var(--law)">판례</div></div>
    <div class="hero-stat" style="border-color:var(--law-border)"><div class="num" style="color:var(--law)">{notice_count}</div><div class="label" style="color:var(--law)">입법예고</div></div>
    <div class="hero-stat" style="border-color:var(--law-border)"><div class="num" style="color:var(--law)">{total_laws}</div><div class="label" style="color:var(--law)">전체 법령</div></div>
  </div>

  <div class="sbox"><span class="si">&#x2315;</span><input id="finlaw-search" placeholder="법령명, 조문, 판례를 검색하세요..." autocomplete="off"></div>
</section>

<div class="divider"></div>
<section class="sec">
  <div class="sec-hdr">최근 법령 변경<a class="sec-more" href="/finlaw/notices/">전체 보기 →</a></div>
{"".join(change_cards) if change_cards else '  <p style="font-size:13px;color:var(--m)">최근 30일간 변경된 법령이 없습니다.</p>'}
</section>

<div class="divider"></div>
<section class="sec">
  <div class="sec-hdr">최근 판례<a class="sec-more" href="/finlaw/cases/">전체 보기 →</a></div>
{"".join(case_cards) if case_cards else '  <p style="font-size:13px;color:var(--m)">최근 판례가 없습니다.</p>'}
</section>

{"" if not notice_cards else f'''<div class="divider"></div>
<section class="sec">
  <div class="sec-hdr">입법예고 트래커<span class="sec-date">{notice_count}건 진행 중</span></div>
{"".join(notice_cards)}
</section>'''}

<div class="divider"></div>
<section class="sec">
  <div class="sec-hdr">법령 데이터베이스<span class="sec-date">{total_laws}개 법령</span></div>
  <div class="fl-grid">
{"".join(db_cards)}
  </div>
</section>

<div style="margin:24px;padding:20px;background:var(--a);border-radius:12px;display:flex;align-items:center;justify-content:space-between;gap:12px">
  <div><h3 style="font-family:var(--serif);font-size:16px;color:#fff">법령 변경 알림</h3><p style="font-size:11px;color:rgba(255,255,255,.6)">텔레그램으로 실시간 알림</p></div>
  <a href="https://t.me/govbrief" target="_blank" style="padding:11px 20px;background:#fff;color:var(--a);border-radius:8px;font-weight:700;font-size:13px;text-decoration:none;white-space:nowrap">구독</a>
</div>

{render_footer()}

{render_bottom_nav("regulation")}
<script>
const finlawSearch = document.getElementById('finlaw-search');
const finlawItems = Array.from(document.querySelectorAll('.finlaw-searchable'));
finlawSearch?.addEventListener('input', function() {{
  const q = this.value.trim().toLowerCase();
  finlawItems.forEach((node) => {{
    node.style.display = !q || node.dataset.search.includes(q) ? '' : 'none';
  }});
}});
finlawSearch?.addEventListener('keydown', function(e) {{
  if (e.key === 'Enter' && !e.isComposing) {{
    const q = this.value.trim();
    if (q) window.location.href = '/tools/finlaw-gpt/?q=' + encodeURIComponent(q);
  }}
}});
</script>
</body>
</html>"""

    # v2 전환: 새 finlaw/index.html 보호
    out = FINLAW_DIR / "index_legacy.html"
    out.write_text(page, encoding="utf-8")
    print(f"[finlaw_pages] index_legacy.html 생성 — 법령 {law_count}건 변경, 판례 {prec_count}건")


def generate_regulation_stats():
    """regulation 페이지용 DB 통계 JSON 생성"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    today = date.today()
    month_ago = (today - timedelta(days=30)).strftime("%Y%m%d")

    # 카테고리별 법령 수
    fin_count = conn.execute("SELECT COUNT(*) FROM laws WHERE categories LIKE '%금융%'").fetchone()[0]
    re_count = conn.execute("SELECT COUNT(*) FROM laws WHERE categories LIKE '%부동산%'").fetchone()[0]
    cross_count = conn.execute("SELECT COUNT(*) FROM laws WHERE categories LIKE '%금융%' AND categories LIKE '%부동산%'").fetchone()[0]

    # 판례/비조치의견서
    prec_count = conn.execute("SELECT COUNT(*) FROM precedents").fetchone()[0]
    try:
        opinion_count = conn.execute("SELECT COUNT(*) FROM fsc_opinions").fetchone()[0]
    except Exception:
        opinion_count = 0

    # 부동산 관련 부처 수
    re_ministries = conn.execute(
        "SELECT COUNT(DISTINCT ministry) FROM laws WHERE categories = '부동산'"
    ).fetchone()[0]

    # 최근 변경 법령 (금융)
    fin_recent = conn.execute(
        "SELECT name, promulgation_date, revision_type, ministry FROM laws "
        "WHERE categories LIKE '%금융%' AND promulgation_date >= ? "
        "ORDER BY promulgation_date DESC LIMIT 5",
        (month_ago,)
    ).fetchall()

    # 최근 변경 법령 (부동산)
    re_recent = conn.execute(
        "SELECT name, promulgation_date, revision_type, ministry FROM laws "
        "WHERE categories LIKE '%부동산%' AND promulgation_date >= ? "
        "ORDER BY promulgation_date DESC LIMIT 5",
        (month_ago,)
    ).fetchall()

    # 교차 법령 목록
    cross_laws = conn.execute(
        "SELECT name, ministry FROM laws "
        "WHERE categories LIKE '%금융%' AND categories LIKE '%부동산%' "
        "ORDER BY name"
    ).fetchall()

    # 법령 참조 관계
    try:
        ref_count = conn.execute("SELECT COUNT(*) FROM law_references").fetchone()[0]
    except Exception:
        ref_count = 0

    conn.close()

    import json
    stats = {
        "generated_at": today.isoformat(),
        "fin_count": fin_count,
        "re_count": re_count,
        "cross_count": cross_count,
        "prec_count": prec_count,
        "opinion_count": opinion_count,
        "re_ministries": re_ministries,
        "ref_count": ref_count,
        "fin_recent": [{"name": r["name"], "date": r["promulgation_date"], "type": r["revision_type"], "ministry": r["ministry"]} for r in fin_recent],
        "re_recent": [{"name": r["name"], "date": r["date"] if "date" in r.keys() else r["promulgation_date"], "type": r["revision_type"], "ministry": r["ministry"]} for r in re_recent],
        "cross_laws": [{"name": r["name"], "ministry": r["ministry"]} for r in cross_laws],
    }

    out_path = BASE_DIR / "data" / "regulation-stats.json"
    out_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[finlaw_pages] regulation-stats.json 생성 — 금융 {fin_count}건, 부동산 {re_count}건, 교차 {cross_count}건, 참조 {ref_count}건")
    return stats


def main():
    generate_finlaw_index()
    generate_cases_page()
    generate_notices_page()
    generate_regulation_stats()
    print("finlaw 페이지 재생성 완료")


if __name__ == "__main__":
    main()
