"""비조치의견서 + 법령해석 목록 페이지 생성

finlaw/opinions/index.html — 3,151건 검색 + 필터

실행: python -m briefingroom.opinions_gen
"""
from __future__ import annotations

import html as h
import re
import sqlite3
from pathlib import Path

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"
OUT_PATH = BASE_DIR / "finlaw" / "opinions" / "index.html"


def _read_css() -> str:
    idx = BASE_DIR / "index.html"
    if idx.exists():
        m = re.search(r"<style>(.*?)</style>", idx.read_text(encoding="utf-8"), re.DOTALL)
        if m:
            return m.group(1)
    return ""


def generate_opinions_page():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT opinion_id, opinion_number, gubun, category, title, status, reg_date, detail_link "
        "FROM fsc_opinions ORDER BY opinion_id DESC"
    ).fetchall()

    # 통계
    by_gubun = {}
    by_cat = {}
    for r in rows:
        g = r["gubun"] or "기타"
        by_gubun[g] = by_gubun.get(g, 0) + 1
        c = r["category"] or "기타"
        by_cat[c] = by_cat.get(c, 0) + 1

    conn.close()

    # 테이블 행 생성
    tbody = []
    for r in rows:
        date = r["reg_date"] or ""
        link = h.escape(r["detail_link"] or "", quote=True)
        gubun_cls = "edit" if "비조치" in (r["gubun"] or "") else "new"
        tbody.append(f"""<tr>
      <td>{h.escape(r['opinion_number'] or '')}</td>
      <td><span style="font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;background:{'#eef2ff' if gubun_cls=='edit' else '#ecfdf5'};color:{'#3730a3' if gubun_cls=='edit' else '#065f46'}">{h.escape(r['gubun'] or '')}</span></td>
      <td>{h.escape(r['category'] or '')}</td>
      <td><a href="{link}" target="_blank" style="text-decoration:none;color:var(--t);font-weight:600">{h.escape(r['title'] or '')}</a></td>
      <td style="font-family:var(--mono);font-size:11px;color:var(--m)">{date}</td>
    </tr>""")

    css = _read_css()

    # 카테고리 탭
    cat_tabs = "".join(f'<span class="dept-tab" data-cat="{h.escape(c)}">{h.escape(c)} ({n})</span>'
                       for c, n in sorted(by_cat.items(), key=lambda x: -x[1])[:10])

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>비조치의견서 · 법령해석 - 브리핑룸</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{css}
table{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px;background:var(--s);border:1px solid var(--b);border-radius:10px;overflow:hidden}}
col.c-no{{width:70px}}col.c-type{{width:70px}}col.c-cat{{width:70px}}col.c-title{{width:auto}}col.c-date{{width:80px}}
th{{background:var(--a);color:#fff;padding:10px 8px;text-align:left;font-size:12px;white-space:nowrap}}
td{{padding:10px 8px;border-bottom:1px solid var(--b);vertical-align:top}}
tr:last-child td{{border-bottom:none}}
@media(max-width:768px){{table{{font-size:11px}}td,th{{padding:8px 6px}}}}
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

<div style="padding:24px 20px 80px">
<a href="/finlaw/" style="color:var(--m);text-decoration:none;font-size:13px;display:inline-block;margin-bottom:16px">← 금융법령 AI 모니터링</a>
<h1 style="font-family:var(--serif);font-size:24px;font-weight:700;margin-bottom:6px">비조치의견서 · 법령해석</h1>
<p style="font-size:14px;color:var(--t2);margin-bottom:16px">금융위원회 비조치의견서 {by_gubun.get('비조치의견서',0)}건 + 법령해석 {by_gubun.get('법령해석',0)}건 = 전체 {len(rows)}건</p>

<div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
  <a href="/finlaw/" style="padding:8px 16px;border-radius:8px;border:1px solid var(--b);background:var(--s);font-size:13px;font-weight:600;color:var(--t);text-decoration:none">법령 목록</a>
  <a href="/finlaw/cases/" style="padding:8px 16px;border-radius:8px;border:1px solid var(--b);background:var(--s);font-size:13px;font-weight:600;color:var(--t);text-decoration:none">판례</a>
  <a href="/finlaw/notices/" style="padding:8px 16px;border-radius:8px;border:1px solid var(--b);background:var(--s);font-size:13px;font-weight:600;color:var(--t);text-decoration:none">법령 개정 이력</a>
  <a href="/finlaw/opinions/" style="padding:8px 16px;border-radius:8px;border:1px solid var(--a);background:var(--a);font-size:13px;font-weight:600;color:#fff;text-decoration:none">비조치의견서 {len(rows)}건</a>
</div>

<div style="position:relative;margin-bottom:12px">
  <span style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--m);font-size:14px">⌕</span>
  <input id="op-search" type="text" placeholder="제목, 분야로 검색..." style="width:100%;padding:12px 14px 12px 36px;font-size:14px;border:2px solid var(--b);border-radius:10px;background:var(--s);color:var(--t);outline:none;font-family:var(--sans)">
</div>
<div style="margin-bottom:12px">
  <span id="result-count" style="font-family:var(--mono);font-size:11px;color:var(--m)"></span>
</div>

<table>
<colgroup><col class="c-no"><col class="c-type"><col class="c-cat"><col class="c-title"><col class="c-date"></colgroup>
<thead><tr><th>번호</th><th>유형</th><th>분야</th><th>제목</th><th>등록일</th></tr></thead>
<tbody>{"".join(tbody)}</tbody>
</table>
</div>

<script>
const rows = document.querySelectorAll('table tbody tr');
const searchInput = document.getElementById('op-search');
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
    r.style.display = terms.every(t => text.includes(t)) ? '' : 'none';
  }});
  updateCount();
}});
updateCount();
</script>

</body>
</html>"""

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(page, encoding="utf-8")
    print(f"[opinions_gen] index.html 생성 — {len(rows)}건")
    return len(rows)


def main():
    generate_opinions_page()


if __name__ == "__main__":
    main()
