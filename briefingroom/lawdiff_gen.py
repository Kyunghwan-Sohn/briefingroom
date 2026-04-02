"""LawDiff 정적 페이지 생성

로컬에서 법제처 API를 호출하여 최근 개정 법령의 신구 조문 대조를 생성합니다.
결과를 finlaw/diff/{mst}/index.html로 저장합니다.

실행: python -m briefingroom.lawdiff_gen
"""
from __future__ import annotations

import html as h
import json
import re
import sqlite3
import time
from pathlib import Path

import requests

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"
DIFF_DIR = BASE_DIR / "finlaw" / "diff"
LAW_OC = "sony0125"

_FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">"""

_CSS = """
:root{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--t);font-family:var(--sans);max-width:960px;margin:0 auto;padding:58px 0 0}
.hdr{position:fixed;top:0;left:0;right:0;z-index:50;max-width:960px;margin:0 auto;background:#f5f5f5;border-bottom:3px solid var(--a);height:54px;display:flex;align-items:center;padding:0 20px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.logo{font-family:var(--serif);font-size:19px;font-weight:700;color:var(--t);text-decoration:none;margin-right:16px;white-space:nowrap}
.hnav{display:flex;gap:0;align-items:center;flex:1;min-width:0}
.hnav a{font-size:14px;font-weight:600;color:var(--m);text-decoration:none;padding:6px 12px;border-radius:5px;white-space:nowrap}
.hnav a.on{color:var(--a);background:var(--al);font-weight:700}
.bell{color:var(--m);text-decoration:none;font-size:14px;font-weight:600;margin-left:auto;flex-shrink:0}
.wrap{padding:24px 20px 80px}
.back{color:var(--m);text-decoration:none;font-size:13px;display:inline-block;margin-bottom:16px}
h1{font-family:var(--serif);font-size:22px;font-weight:700;margin-bottom:8px;line-height:1.4}
.meta{font-size:12px;color:var(--m);margin-bottom:20px;display:flex;gap:16px;flex-wrap:wrap}
.summary{background:var(--s);border:1px solid var(--b);border-radius:10px;padding:16px;margin-bottom:16px;display:flex;gap:16px;font-family:var(--mono);font-size:13px}
.stat-mod{color:var(--a);font-weight:700}
.stat-add{color:#059669;font-weight:700}
.stat-del{color:#dc2626;font-weight:700}
.diff-card{background:var(--s);border:1px solid var(--b);border-radius:10px;margin-bottom:10px;overflow:hidden}
.diff-head{padding:12px 16px;border-bottom:1px solid var(--bl);display:flex;align-items:center;gap:8px}
.diff-tag{font-size:9px;font-weight:700;padding:3px 8px;border-radius:4px}
.diff-tag.modified{background:#fff7ed;color:#9a3412}
.diff-tag.added{background:#ecfdf5;color:#065f46}
.diff-tag.deleted{background:#fef2f2;color:#991b1b}
.diff-title{font-size:14px;font-weight:600}
.diff-row{display:flex;font-family:var(--mono);font-size:12px;line-height:1.6}
.diff-old{flex:1;padding:10px 12px;background:#fef2f2;color:#991b1b;white-space:pre-wrap;word-break:break-all}
.diff-new{flex:1;padding:10px 12px;background:#ecfdf5;color:#065f46;border-left:1px solid var(--bl);white-space:pre-wrap;word-break:break-all}
.diff-label-row{display:flex}
.diff-label{flex:1;font-size:10px;font-weight:700;color:var(--m);padding:6px 12px;background:var(--bg);text-align:center}
.footer{padding:20px 24px;text-align:center;font-size:10px;color:var(--m)}
.footer a{color:var(--t);text-decoration:none;font-weight:600}
@media(max-width:768px){body{padding-top:52px}.hdr{height:50px;padding:0 14px}.logo{font-size:17px}.hnav a{font-size:11px;padding:5px 8px}.diff-row{flex-direction:column}.diff-new{border-left:none;border-top:1px solid var(--bl)}}
"""

_HEADER = """<header class="hdr">
  <a class="logo" href="/">브리핑룸</a>
  <nav class="hnav">
    <a href="/">정책 AI 요약</a>
    <a href="/finlaw/">금융법령 AI 모니터링</a>
  </nav>
  <a class="bell" href="https://t.me/govbrief" target="_blank">알림</a>
</header>"""


def _fetch_articles(mst: str) -> list[dict]:
    """법제처 API에서 조문 가져오기"""
    try:
        r = requests.get(
            "https://www.law.go.kr/DRF/lawService.do",
            params={"OC": LAW_OC, "target": "law", "MST": mst, "type": "JSON"},
            timeout=20,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        if "실패" in str(data.get("result", "")):
            return []
        jomun = data.get("법령", {}).get("조문", {}).get("조문단위", [])
        if isinstance(jomun, dict):
            jomun = [jomun]
        result = []
        for j in jomun:
            content = j.get("조문내용", "")
            hangs = j.get("항", [])
            if isinstance(hangs, dict):
                hangs = [hangs]
            for hang in hangs:
                if isinstance(hang, dict):
                    content += "\n" + hang.get("항내용", "")
            result.append({
                "key": j.get("조문키", ""),
                "no": j.get("조문번호", ""),
                "title": j.get("조문제목", ""),
                "content": content.strip(),
            })
        return result
    except Exception as e:
        print(f"  API 에러: {e}")
        return []


def generate_diffs():
    """최근 개정 법령의 조문 변경 내역을 추출하여 diff 페이지 생성"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT law_mst, name, name_abbr, ministry, revision_type, "
        "promulgation_date, enforcement_date "
        "FROM laws WHERE promulgation_date >= '20250101' "
        "AND revision_type IN ('일부개정') "
        "ORDER BY promulgation_date DESC"
    ).fetchall()
    conn.close()

    DIFF_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0

    for r in rows:
        mst = r["law_mst"]
        if not mst:
            continue

        out_dir = DIFF_DIR / mst
        out_path = out_dir / "index.html"
        if out_path.exists():
            continue

        print(f"  [{mst}] {r['name'][:40]}")

        # 현행 조문 가져오기
        articles = _fetch_articles(mst)
        if not articles:
            print(f"    조문 없음, 건너뜀")
            time.sleep(0.5)
            continue

        # 최근 개정 조문 추출 (본문에 <개정 2024~ 또는 2025~> 포함)
        changed = []
        for a in articles:
            dates = re.findall(r"개정 (\d{4}\.\d{1,2}\.\d{1,2})", a["content"])
            if dates:
                latest = max(dates)
                if latest >= "2024":
                    changed.append({**a, "amend_date": latest})

        if not changed:
            print(f"    최근 개정 조문 없음")
            time.sleep(0.5)
            continue

        # HTML 생성
        name = h.escape(r["name"])
        abbr = h.escape(r["name_abbr"] or "")
        prom = r["promulgation_date"] or ""
        if len(prom) == 8:
            prom = f"{prom[:4]}.{prom[4:6]}.{prom[6:]}"

        diff_cards = []
        for c in changed:
            content = h.escape(c["content"][:600])
            diff_cards.append(f"""<div class="diff-card">
  <div class="diff-head">
    <span class="diff-tag modified">변경</span>
    <span class="diff-title">제{c['no']}조 {h.escape(c['title'])}</span>
    <span style="margin-left:auto;font-family:var(--mono);font-size:10px;color:var(--a)">개정 {c['amend_date']}</span>
  </div>
  <div style="padding:12px 16px;font-size:13px;color:var(--t2);line-height:1.7;white-space:pre-wrap">{content}</div>
</div>""")

        page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} 개정 조문 - 브리핑룸</title>
{_FONTS}
<style>{_CSS}</style>
</head>
<body>
{_HEADER}
<div class="wrap">
<a class="back" href="/finlaw/detail/{mst}/">← {name}</a>
<h1>{name} — 개정 조문</h1>
<div class="meta">
  <span>{abbr}</span>
  <span>공포 {prom}</span>
  <span>{h.escape(r['revision_type'])}</span>
  <span>전체 {len(articles)}개 조문 중 {len(changed)}건 변경</span>
</div>

<div class="summary">
  <span>전체 <strong>{len(articles)}</strong>개 조문</span>
  <span class="stat-mod">변경 <strong>{len(changed)}</strong></span>
</div>

{"".join(diff_cards)}

</div>
<div class="footer"><a href="/">정책 AI 요약</a> · <a href="/finlaw/">금융법령 AI 모니터링</a><br>govbrief.kr</div>
</body>
</html>"""

        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page, encoding="utf-8")
        generated += 1
        print(f"    → diff 생성 ({len(changed)}건 변경)")
        time.sleep(0.5)

    print(f"[lawdiff_gen] {generated}건 diff 페이지 생성")
    return generated


def main():
    print("=" * 50)
    print("LawDiff 정적 페이지 생성")
    print("=" * 50)
    generate_diffs()


if __name__ == "__main__":
    main()
