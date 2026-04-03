"""articles/index.html 생성 — 날짜별 보도자료 목록 페이지

실행: python -m briefingroom.articles_gen
"""
from __future__ import annotations

import html as h
import json
import os
from datetime import date
from pathlib import Path

from briefingroom.config import BASE_DIR, DATA_DIR
from briefingroom.site_templates import render_top_nav, render_footer

ARTICLES_DIR = BASE_DIR / "articles"

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def _read_css() -> str:
    idx = BASE_DIR / "index.html"
    if idx.exists():
        import re
        m = re.search(r"<style>(.*?)</style>", idx.read_text(encoding="utf-8"), re.DOTALL)
        if m:
            return m.group(1)
    return ""


def generate_articles_index():
    """articles/index.html — 날짜별 보도자료 목록"""
    # 날짜별 JSON 파일 수집
    json_files = sorted(
        [f for f in DATA_DIR.iterdir() if f.name.startswith("2026-") and f.suffix == ".json"
         and "weekly" not in f.name and "schedule" not in f.name and "subsidies" not in f.name
         and "latest" not in f.name],
        reverse=True,
    )

    days = []
    for jf in json_files[:30]:  # 최근 30일
        try:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("items", data) if isinstance(data, dict) else data
            if not items:
                continue
            d = jf.stem  # 2026-03-31
            from datetime import datetime
            dt = datetime.strptime(d, "%Y-%m-%d")
            dow = _WEEKDAYS[dt.weekday()]

            # 카테고리별 건수
            cats = {}
            for it in items:
                c = it.get("category", "기타")
                cats[c] = cats.get(c, 0) + 1

            # 상위 3건
            top3 = []
            for it in items[:5]:
                slug = it.get("slug") or "000"
                detail_exists = (ARTICLES_DIR / d / slug / "detail.html").exists()
                article_exists = (ARTICLES_DIR / d / slug / "index.html").exists()
                link = f"/articles/{d}/{slug}/detail.html" if detail_exists else (
                    f"/articles/{d}/{slug}/" if article_exists else "#"
                )
                top3.append({
                    "title": it.get("title", "")[:60],
                    "source": it.get("source", ""),
                    "impact": it.get("impact", "중"),
                    "link": link,
                })

            days.append({
                "date": d,
                "dow": dow,
                "count": len(items),
                "cats": cats,
                "top3": top3,
            })
        except Exception:
            continue

    css = _read_css()

    # 날짜 카드 HTML
    day_cards = []
    for day in days:
        cat_tags = " · ".join(f"{c} {n}건" for c, n in sorted(day["cats"].items(), key=lambda x: -x[1])[:4])
        top_html = ""
        for t in day["top3"][:3]:
            imp_color = "#dc2626" if t["impact"] == "상" else ("var(--a)" if t["impact"] == "중" else "var(--m)")
            top_html += f'<a href="{h.escape(t["link"], quote=True)}" style="display:block;padding:8px 0;border-bottom:1px solid var(--bl);text-decoration:none;color:var(--t);font-size:13px;line-height:1.5"><span style="font-family:var(--mono);font-size:9px;padding:2px 5px;border-radius:3px;background:var(--al);color:{imp_color};margin-right:6px">{h.escape(t["impact"])}</span>{h.escape(t["source"][:3])} — {h.escape(t["title"])}</a>'

        day_cards.append(f"""<div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:18px;margin-bottom:12px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div>
      <span style="font-family:var(--serif);font-size:18px;font-weight:700">{day["date"]}</span>
      <span style="font-size:12px;color:var(--m);margin-left:6px">({day["dow"]})</span>
    </div>
    <span style="font-family:var(--mono);font-size:12px;color:var(--a);font-weight:700">{day["count"]}건</span>
  </div>
  <div style="font-size:11px;color:var(--t2);margin-bottom:10px">{h.escape(cat_tags)}</div>
  {top_html}
</div>""")

    nav_html = render_top_nav("archive")
    footer_html = render_footer()

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>보도자료 아카이브 - 브리핑룸</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>

{nav_html}

<div style="padding:24px 20px 80px">
<h1 style="font-family:var(--serif);font-size:24px;font-weight:700;margin-bottom:6px">보도자료 아카이브</h1>
<p style="font-size:14px;color:var(--t2);margin-bottom:14px">51개 부처 보도자료 날짜별 브리핑 + 주간 리포트</p>
<div style="display:flex;gap:8px;margin-bottom:20px">
  <a href="/articles/weekly/" style="display:inline-block;padding:8px 16px;border-radius:8px;background:#1e40af;color:#fff;font-size:13px;font-weight:600;text-decoration:none">주간 리포트</a>
</div>

{"".join(day_cards)}

</div>

{footer_html}

</body>
</html>"""

    out = ARTICLES_DIR / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"[articles_gen] index.html 생성 — {len(days)}일")
    return len(days)


def main():
    generate_articles_index()


if __name__ == "__main__":
    main()
