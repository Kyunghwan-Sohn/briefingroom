"""finlaw 정적 페이지 재생성

finance_law.db에서 데이터를 읽어 finlaw/cases/index.html, finlaw/notices/index.html을 재생성합니다.
개정이유(amendment_reason), 판례요지(summary) 포함.

실행: python -m briefingroom.finlaw_pages
"""
from __future__ import annotations

import html
import re
import sqlite3
from pathlib import Path

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"
FINLAW_DIR = BASE_DIR / "finlaw"


def _clean_html(text: str) -> str:
    """HTML 태그 제거 + 정리"""
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200]


def generate_cases_page():
    """판례 페이지 재생성 — summary 컬럼 포함"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT prec_id, case_name, case_number, court, decision_date, "
        "summary, detail_link FROM precedents ORDER BY decision_date DESC"
    ).fetchall()
    conn.close()

    tbody = []
    for r in rows:
        date = r["decision_date"] or ""
        court = r["court"] or ""
        name = html.escape(r["case_name"] or "")
        number = html.escape(r["case_number"] or "")
        summary = _clean_html(r["summary"] or "")
        link = html.escape(r["detail_link"] or "", quote=True)

        summary_html = ""
        if summary and summary != "-":
            summary_html = f'<div style="font-size:11px;color:var(--t2);margin-top:4px;line-height:1.5">{html.escape(summary)}</div>'

        tbody.append(f"""<tr>
      <td>{date}</td>
      <td>{html.escape(court)}</td>
      <td><div style="font-weight:600">{name}</div><div style="font-size:11px;color:var(--m);margin-top:2px">{number}</div>{summary_html}</td>
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
:root{{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}}
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
<header class="hdr">
  <a class="logo" href="/">브리핑룸</a>
  <nav class="hnav">
    <a href="/">정책 AI 요약</a>
    <a class="on" href="/finlaw/">금융법령 AI 모니터링</a>
  </nav>
  <a class="bell" href="https://t.me/govbrief" target="_blank">알림</a>
</header>
<div class="wrap">
<a class="back" href="/finlaw/">← 금융법령 AI 모니터링</a>
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
    rows = conn.execute(
        "SELECT name, promulgation_date, revision_type, ministry, "
        "detail_link, amendment_reason FROM laws "
        "WHERE promulgation_date >= '20250101' "
        "ORDER BY promulgation_date DESC"
    ).fetchall()
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
:root{{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}}
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
<header class="hdr">
  <a class="logo" href="/">브리핑룸</a>
  <nav class="hnav">
    <a href="/">정책 AI 요약</a>
    <a class="on" href="/finlaw/">금융법령 AI 모니터링</a>
  </nav>
  <a class="bell" href="https://t.me/govbrief" target="_blank">알림</a>
</header>
<div class="wrap">
<a class="back" href="/finlaw/">← 금융법령 AI 모니터링</a>
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


def main():
    generate_cases_page()
    generate_notices_page()
    print("finlaw 페이지 재생성 완료")


if __name__ == "__main__":
    main()
