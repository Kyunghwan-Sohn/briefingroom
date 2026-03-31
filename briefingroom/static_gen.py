"""정적 사이트 생성기 — RSS 피드 + 개별 기사 HTML 생성"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

from briefingroom.config import DATA_DIR
from briefingroom.site_templates import SITE_NAV_CSS, render_crosslinks, render_top_nav

SITE_URL = "https://govbrief.kr"
SITE_TITLE = "브리핑룸 — 정부 보도자료 AI 요약"
SITE_DESC = "대한민국 51개 정부 부처 + 금융기관 보도자료를 매일 자동 수집하고 AI가 요약합니다."

FEED_DIR = Path(DATA_DIR).parent / "feed"
ARTICLES_DIR = Path(DATA_DIR).parent / "articles"


def _safe_url(value: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return html.escape(url, quote=True)
    return ""


def _build_law_section(laws: list) -> str:
    """관련 법령 HTML 섹션 생성"""
    if not laws:
        return ""
    rows = ""
    for law in laws:
        name = html.escape(law.get("law_name", ""))
        ref = html.escape(law.get("article_ref", ""))
        ministry = html.escape(law.get("ministry", ""))
        ef_date = law.get("enforcement_date", "")
        link = law.get("detail_link", "")
        if link and not link.startswith("http"):
            link = f"https://www.law.go.kr{link}"

        ref_text = f" {ref}" if ref else ""
        date_text = f" · 시행 {ef_date[:4]}.{ef_date[4:6]}.{ef_date[6:]}" if len(ef_date) == 8 else ""
        link_html = f' <a href="{html.escape(link)}" target="_blank" rel="noopener" style="font-family:var(--mono,monospace);font-size:11px;color:#1d70b8;text-decoration:none">법령 전문 보기 →</a>' if link else ""

        rows += f"""<div style="padding:10px 0;border-bottom:1px solid #d8d4cb">
          <div style="font-size:14px;font-weight:600;color:#1c1b18">{name}{ref_text}</div>
          <div style="font-size:11px;color:#6f6b63;margin-top:3px">{ministry}{date_text}{link_html}</div>
        </div>"""

    return f"""<section class="info-section law-section">
      <div class="section-kicker">Related Laws</div>
      <h3>관련 법령</h3>
      <div class="law-box">
        {rows}
      </div>
    </section>"""


def _build_context_section(title: str, body: str, class_name: str, kicker: str) -> str:
    text = (body or "").strip()
    if not text:
        return ""
    return f"""<section class="info-section {class_name}">
      <div class="section-kicker">{html.escape(kicker)}</div>
      <h3>{html.escape(title)}</h3>
      <p>{html.escape(text)}</p>
    </section>"""


def _build_keyword_section(keywords: list[str]) -> str:
    if not keywords:
        return ""
    return f"""<div class='keywords'>{"".join(f"<span>#{html.escape(k)}</span>" for k in keywords)}</div>"""


def _build_summary_section(summary: str) -> str:
    text = (summary or "").strip() or "요약이 준비 중입니다."
    return f"""<section class="summary">
      <div class="section-kicker">Briefing Summary</div>
      <h3>요약</h3>
      <p>{html.escape(text)}</p>
    </section>"""


def _build_original_link(url: str) -> str:
    return f"""<div class="links">
      <h4>원문</h4>
      <a href="{url or '#'}" target="_blank" rel="noopener noreferrer">원문 보기 →</a>
    </div>"""


def generate_rss(target_date: str, max_items: int = 50) -> Path:
    """일별 JSON에서 RSS 2.0 XML 생성"""
    json_path = DATA_DIR / f"{target_date}.json"
    if not json_path.exists():
        print(f"  [RSS] {json_path} 없음 → 스킵")
        return None

    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])[:max_items]

    rss_items = []
    for it in items:
        title = xml_escape(it.get("title", ""))
        source = xml_escape(it.get("source", ""))
        summary = xml_escape(it.get("summary", ""))
        link = xml_escape(it.get("url", ""))
        date_str = it.get("date", target_date)
        category = xml_escape(it.get("category", ""))
        keywords = it.get("keywords", [])
        kw_html = " ".join(f"#{xml_escape(k)}" for k in keywords) if keywords else ""

        pub_date = datetime.strptime(date_str, "%Y-%m-%d").strftime(
            "%a, %d %b %Y 09:00:00 +0900"
        )

        description = f"[{source}] {summary}" if summary else f"[{source}] {title}"
        if kw_html:
            description += f" | {kw_html}"

        rss_items.append(f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{xml_escape(description)}</description>
      <category>{category}</category>
      <pubDate>{pub_date}</pubDate>
      <source url="{SITE_URL}">{xml_escape(SITE_TITLE)}</source>
    </item>""")

    build_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0900")

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{xml_escape(SITE_TITLE)}</title>
    <link>{SITE_URL}</link>
    <description>{xml_escape(SITE_DESC)}</description>
    <language>ko</language>
    <lastBuildDate>{build_date}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed/rss.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(rss_items)}
  </channel>
</rss>
"""

    FEED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FEED_DIR / "rss.xml"
    out_path.write_text(rss_xml, encoding="utf-8")
    print(f"  [RSS] {out_path} 생성 ({len(rss_items)}건)")
    return out_path


def generate_article_pages(target_date: str) -> int:
    """개별 기사 정적 HTML 생성 (SEO용 meta + JSON-LD)"""
    json_path = DATA_DIR / f"{target_date}.json"
    if not json_path.exists():
        return 0

    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    count = 0

    date_dir = ARTICLES_DIR / target_date
    date_dir.mkdir(parents=True, exist_ok=True)

    for idx, it in enumerate(items):
        title = it.get("title", "")
        source = it.get("source", "")
        summary = it.get("summary", "")
        why_important = it.get("why_important", "")
        practical_impact = it.get("practical_impact", "")
        url = _safe_url(it.get("url", ""))
        date_str = it.get("date", target_date)
        category = it.get("category", "")
        keywords = it.get("keywords", [])

        slug = it.get("slug") or f"{idx:03d}"
        article_url = f"{SITE_URL}/articles/{target_date}/{slug}/"
        kw_json = json.dumps(keywords, ensure_ascii=False)
        weekly_link = f"{SITE_URL}/articles/weekly/{target_date}/"
        schedule_link = f"{SITE_URL}/articles/schedule/{target_date}/"
        subsidy_link = f"{SITE_URL}/subsidy/"

        h_title = html.escape(title)
        h_source = html.escape(source)
        h_summary = html.escape(summary)
        desc = f"[{source}] {summary[:120]}" if summary else f"[{source}] {title}"
        h_desc = html.escape(desc)

        article_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{h_title} - 브리핑룸</title>
<meta name="description" content="{h_desc}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{article_url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{h_title} - 브리핑룸">
<meta property="og:description" content="{h_desc}">
<meta property="og:url" content="{article_url}">
<meta property="og:site_name" content="브리핑룸">
<meta property="og:locale" content="ko_KR">
<meta property="article:published_time" content="{date_str}T09:00:00+09:00">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{h_title} - 브리핑룸">
<meta name="twitter:description" content="{h_desc}">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": {json.dumps(title, ensure_ascii=False)},
  "datePublished": "{date_str}T09:00:00+09:00",
  "description": {json.dumps(desc, ensure_ascii=False)},
  "url": "{article_url}",
  "publisher": {{
    "@type": "Organization",
    "name": "브리핑룸",
    "url": "{SITE_URL}"
  }},
  "keywords": {kw_json},
  "mainEntityOfPage": "{article_url}"
}}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&family=Pretendard:wght@400;600;700&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root{{--bg:#f5f4f0;--bg2:#eceae5;--surface:#fff;--border:#e0ddd7;--text:#1c1b18;--text2:#4a4844;--muted:#96938c;--accent:#2f54eb;--accent-l:#eef0fd;--serif:'Noto Serif KR',serif;--sans:'Pretendard',sans-serif;--mono:'DM Mono',monospace}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;background-image:radial-gradient(circle at 1px 1px,var(--border) 1px,transparent 0);background-size:24px 24px;opacity:.5;pointer-events:none;z-index:0}}
.wrap{{max-width:720px;margin:0 auto;padding:32px 24px;position:relative;z-index:1}}
.back{{display:inline-flex;align-items:center;gap:6px;color:var(--muted);text-decoration:none;font-family:var(--mono);font-size:12px;margin-bottom:24px;padding:7px 14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;transition:all .15s}}
.back:hover{{color:var(--text)}}
{SITE_NAV_CSS}
.post-badge{{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:11px;padding:4px 12px;border-radius:6px;background:var(--accent-l);color:var(--accent);border:1px solid rgba(47,84,235,.2);margin-bottom:14px}}
.post-title{{font-family:var(--serif);font-size:26px;font-weight:700;letter-spacing:-.5px;line-height:1.35;color:var(--text);margin-bottom:20px}}
.post-meta{{display:flex;gap:20px;padding:14px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-bottom:24px}}
.meta-i{{font-family:var(--mono);font-size:11px;color:var(--muted);display:flex;flex-direction:column;gap:3px}}
.meta-i strong{{color:var(--text2);font-weight:500}}
.post-content{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px}}
.summary h3,.info-section h3{{font-family:var(--serif);font-size:16px;font-weight:600;color:var(--text);margin:0 0 10px}}
.section-kicker{{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#7a735f;margin-bottom:8px}}
.summary p{{font-size:14px;color:var(--text2);line-height:1.8;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:14px 16px}}
.info-section{{margin-top:18px}}
.info-section p{{font-size:14px;line-height:1.8;padding:14px 16px;border-radius:8px;border:1px solid var(--border);background:#fff}}
.why-box p{{border-left:4px solid var(--accent);background:#f4f7ff}}
.impact-box p{{border-left:4px solid #d97706;background:#fff7ed}}
.law-box{{background:#f3f2f1;border:1px solid #d8d4cb;border-radius:8px;padding:4px 14px}}
.keywords{{display:flex;flex-wrap:wrap;gap:5px;margin:16px 0}}
.keywords span{{font-family:var(--mono);font-size:11px;color:#fff;background:#2f54eb;padding:4px 10px;border-radius:4px;font-weight:500}}
.links h4{{font-family:var(--serif);font-size:14px;font-weight:600;color:var(--text);margin:16px 0 8px}}
.links a{{color:#1d70b8;text-decoration:none;font-size:13px;font-family:var(--mono)}}
.links a:hover{{text-decoration:underline}}
@media(max-width:768px){{.wrap{{padding:20px 16px}}.post-title{{font-size:20px}}}}
</style>
</head>
<body>
<div class="wrap">
  {render_top_nav("")}
  <a class="back" href="/">&#8592; 브리핑룸으로</a>
  {render_crosslinks((weekly_link, "주간 리포트"), (schedule_link, "차주 일정"), (subsidy_link, "지원사업"))}
  <div class="post-badge">🏛 {h_source} 보도자료</div>
  <h1 class="post-title">{h_title}</h1>
  <div class="post-meta">
    <div class="meta-i"><span>날짜</span><strong>{date_str}</strong></div>
    <div class="meta-i"><span>분야</span><strong>{html.escape(category)}</strong></div>
    <div class="meta-i"><span>기관</span><strong>{h_source}</strong></div>
  </div>
  <div class="post-content">
    {_build_summary_section(summary)}
    {_build_context_section("왜 중요한가", why_important, "why-box", "Why It Matters")}
    {_build_keyword_section(keywords)}
    {_build_law_section(it.get("related_laws", []))}
    {_build_context_section("실무 영향", practical_impact, "impact-box", "Practical Impact")}
    {_build_original_link(url)}
  </div>
</div>
</body>
</html>
"""

        article_dir = date_dir / slug
        article_dir.mkdir(parents=True, exist_ok=True)
        (article_dir / "index.html").write_text(article_html, encoding="utf-8")
        count += 1

    print(f"  [Articles] {count}개 기사 HTML 생성 → {date_dir}")
    return count



def generate_sitemap(target_date: str) -> Path:
    """sitemap.xml 생성 — 날짜별 아카이브 + 기사 페이지 URL"""
    import glob as _glob

    urls = [f'  <url><loc>{SITE_URL}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>']

    # 날짜별 JSON에서 기사 URL 수집
    for json_file in sorted(Path(DATA_DIR).glob("20*.json")):
        date_str = json_file.stem
        data = json.loads(json_file.read_text(encoding="utf-8"))
        items = data.get("items", [])
        for idx, item in enumerate(items):
            slug = item.get("slug") or f"{idx:03d}"
            urls.append(f'  <url><loc>{SITE_URL}/articles/{date_str}/{slug}/</loc><lastmod>{date_str}</lastmod></url>')

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""

    out_path = Path(DATA_DIR).parent / "sitemap.xml"
    out_path.write_text(sitemap_xml, encoding="utf-8")
    print(f"  [Sitemap] {out_path} 생성 ({len(urls)}개 URL)")
    return out_path


def generate_static(target_date: str) -> None:
    """정적 사이트 전체 생성 (RSS + 기사 페이지)"""
    print(f"\n{'─' * 60}")
    print("[정적 사이트 생성 중...]")
    generate_rss(target_date)
    generate_article_pages(target_date)
    generate_sitemap(target_date)
