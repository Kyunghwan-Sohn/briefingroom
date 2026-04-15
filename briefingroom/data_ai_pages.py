"""데이터/AI 규제 트래커 페이지 생성기

finance_law.db에서 데이터/AI 관련 법령을 읽어
법령 상세 페이지와 타임라인 페이지를 생성합니다.

실행: python -m briefingroom.data_ai_pages
"""
from __future__ import annotations

import html as h
import json
import sqlite3
from pathlib import Path

import time as _time
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

from briefingroom.config import BASE_DIR, DATA_DIR

DB_PATH = BASE_DIR / "finance_law.db"
DATA_AI_DIR = BASE_DIR / "regulation" / "data-ai"
SITE_URL = "https://govbrief.kr"

CAT_COLORS = {
    "데이터": ("#1e40af", "#eff6ff"),
    "인공지능": ("#047857", "#ecfdf5"),
    "디지털": ("#d97706", "#fef3c7"),
    "개인정보": ("#1e40af", "#eff6ff"),
    "전자금융": ("#d97706", "#fef3c7"),
    "여신신용": ("#1e40af", "#eff6ff"),
    "자금세탁": ("#1e40af", "#eff6ff"),
    "기타금융": ("#d97706", "#fef3c7"),
}

COMMON_CSS = """
*{box-sizing:border-box;margin:0;padding:0;word-break:keep-all}
:root{--bg:#f7f7f5;--s:#fff;--b:#dcdcd8;--bl:#ededea;--t:#1a1a1a;--t2:#555;--t3:#888;--m:#bbb;--sec:#7c3aed;--sec-bg:#f5f3ff;--sec-border:#ddd6fe;--data:#1e40af;--data-bg:#eff6ff;--ai:#047857;--ai-bg:#ecfdf5;--digital:#d97706;--digital-bg:#fef3c7;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}
body{background:var(--bg);color:var(--t);font-family:var(--sans);font-size:16px;line-height:1.7;min-width:1120px}
.is-mobile body{min-width:0;font-size:15px;padding-bottom:68px}
.hdr{background:#fff;border-bottom:1px solid var(--b);height:64px;display:flex;align-items:center;padding:0 32px;position:sticky;top:0;z-index:100}
.hdr-logo{font-family:var(--serif);font-size:24px;font-weight:700;color:var(--t);text-decoration:none;margin-right:44px}
.hdr-nav{display:flex;gap:6px;flex:1}
.hdr-nav a{font-size:15px;font-weight:600;color:var(--t2);text-decoration:none;padding:10px 16px;border-radius:6px}
.hdr-nav a:hover{background:var(--bl)}
.hdr-nav a.on{color:var(--sec);background:var(--sec-bg);font-weight:700}
.is-mobile .hdr{height:52px;padding:0 12px}
.is-mobile .hdr-logo{font-size:17px;margin-right:8px}
.is-mobile .hdr-nav a{font-size:12px;padding:7px 8px}
"""

HEADER_HTML = """<header class="hdr">
  <a class="hdr-logo" href="/">브리핑룸</a>
  <nav class="hdr-nav">
    <a href="/">홈</a>
    <a href="/brief/">정부 발표</a>
    <a href="/keywords/">키워드 트렌드</a>
    <a class="on" href="/regulation/">규제 트래커</a>
  </nav>
</header>"""

FOOTER_HTML = """<footer style="max-width:1080px;margin:20px auto 0;padding:24px 16px;text-align:center;color:var(--t3);border-top:1px solid var(--bl)">
  <div style="font-family:var(--serif);font-size:14px;color:var(--t2)">정부 정책과 규제 변화, 한 화면에</div>
  <div style="font-family:var(--mono);font-size:11px;color:var(--t3);margin-top:4px">govbrief.kr</div>
</footer>
<nav class="bnav"><a href="/">홈</a><a href="/brief/">정부 발표</a><a href="/keywords/">키워드</a><a class="on" href="/regulation/">규제</a></nav>"""


def _get_data_ai_laws(conn: sqlite3.Connection) -> list[dict]:
    """데이터/AI 관련 법령 + 조문 가져오기"""
    rows = conn.execute("""
        SELECT law_id, name, category, categories, ministry, law_type,
               promulgation_date, enforcement_date, article_count, amendment_reason
        FROM laws
        WHERE categories LIKE '%데이터AI%'
        ORDER BY enforcement_date DESC
    """).fetchall()

    laws = []
    for r in rows:
        law_id = r[0]
        articles = conn.execute("""
            SELECT article_no, article_title, article_content
            FROM articles WHERE law_id = ?
            ORDER BY CAST(article_no AS INTEGER)
        """, (law_id,)).fetchall()

        # 카테고리 결정
        cat = r[2] or "데이터"
        if cat in ("개인정보", "여신신용", "자금세탁"):
            cat_label = "데이터"
        elif cat in ("인공지능",):
            cat_label = "인공지능"
        else:
            cat_label = "디지털"

        laws.append({
            "law_id": law_id,
            "name": r[1],
            "category": r[2],
            "cat_label": cat_label,
            "ministry": r[4] or "",
            "law_type": r[5] or "",
            "promulgation_date": r[6] or "",
            "enforcement_date": r[7] or "",
            "article_count": len(articles),
            "amendment_reason": r[9] or "",
            "articles": [{"no": a[0], "title": a[1], "content": a[2]} for a in articles],
        })

    return laws


def _build_analysis_html(analysis: dict, color: str) -> str:
    """LLM 분석 결과를 HTML로 변환"""
    if not analysis or not analysis.get("background"):
        return ""

    sections = []

    # 개정 배경
    if analysis.get("background"):
        sections.append(f"""<div class="sec-hdr">개정 배경</div>
<div style="background:var(--sec-bg);border-left:4px solid var(--sec);border-radius:0 10px 10px 0;padding:18px 24px;margin-bottom:16px;font-size:16px;color:var(--t);line-height:1.9">{h.escape(analysis['background'])}</div>""")

    # 핵심 변경
    if analysis.get("changes"):
        items = ""
        for i, change in enumerate(analysis["changes"], 1):
            if " - " in change:
                title, desc = change.split(" - ", 1)
                text = f"<strong>{h.escape(title)}</strong> - {h.escape(desc)}"
            else:
                text = h.escape(change)
            items += f'<div style="display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-top:1px dashed var(--bl)"><span style="font-family:var(--mono);font-size:12px;font-weight:700;color:{color};background:var(--sec-bg);border-radius:4px;padding:3px 8px;flex-shrink:0">{i:02d}</span><div style="font-size:15px;color:var(--t);line-height:1.8">{text}</div></div>'
        sections.append(f"""<div class="sec-hdr">핵심 변경사항</div>
<div style="background:#fff;border:1px solid var(--b);border-radius:10px;padding:18px 22px;margin-bottom:16px">{items}</div>""")

    # 실무 영향
    if analysis.get("impact"):
        sections.append(f"""<div class="sec-hdr">실무 영향</div>
<div style="background:#fff;border:1px solid var(--b);border-radius:10px;padding:18px 22px;margin-bottom:16px">
<div style="border-left:4px solid {color};background:var(--sec-bg);border-radius:0 10px 10px 0;padding:16px 20px;font-size:16px;color:var(--t);line-height:1.9">{h.escape(analysis['impact'])}</div>
</div>""")

    # 대상 기업 + 위반 시 제재
    meta_items = []
    if analysis.get("target"):
        meta_items.append(f'<div style="padding:10px 0;border-bottom:1px dashed var(--bl)"><div style="font-size:12px;font-weight:700;color:{color};margin-bottom:4px">영향 대상</div><div style="font-size:15px;color:var(--t2);line-height:1.7">{h.escape(analysis["target"])}</div></div>')
    if analysis.get("penalty"):
        meta_items.append(f'<div style="padding:10px 0"><div style="font-size:12px;font-weight:700;color:#dc2626;margin-bottom:4px">위반 시 제재</div><div style="font-size:15px;color:var(--t2);line-height:1.7">{h.escape(analysis["penalty"])}</div></div>')
    if meta_items:
        sections.append(f"""<div style="background:#fff;border:1px solid var(--b);border-radius:10px;padding:14px 22px;margin-bottom:16px">{''.join(meta_items)}</div>""")

    # 관련 키워드
    if analysis.get("keywords"):
        kws = "".join(f'<span style="font-size:13px;font-weight:600;padding:5px 12px;border-radius:10px;border:1px solid var(--sec-border);color:{color}">{h.escape(kw)}</span>' for kw in analysis["keywords"])
        sections.append(f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px">{kws}</div>')

    return "\n".join(sections)


NEWS_CACHE = DATA_DIR / "data-ai-news.json"


def _load_news_cache() -> dict:
    if NEWS_CACHE.exists():
        return json.loads(NEWS_CACHE.read_text(encoding="utf-8"))
    return {}


def _save_news_cache(cache: dict):
    NEWS_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_law_news(law_name: str, max_results: int = 5) -> list[dict]:
    """Google News RSS로 법령 관련 뉴스 가져오기"""
    query = quote(f"{law_name} 개정")
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 govbrief.kr"})
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
        articles = []
        for item in root.findall(".//item")[:max_results]:
            title = item.find("title").text or ""
            source = item.find("source").text if item.find("source") is not None else ""
            link = item.find("link").text or ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            articles.append({
                "title": title.replace(f" - {source}", "").strip(),
                "source": source,
                "link": link,
                "pub_date": pub_date,
            })
        return articles
    except Exception as e:
        print(f"  [News] {law_name} 뉴스 조회 실패: {e}")
        return []


def _get_law_news(law_name: str, news_cache: dict) -> list[dict]:
    """뉴스 캐시에서 가져오거나 새로 크롤링"""
    if law_name in news_cache:
        return news_cache[law_name]
    print(f"  [News] {law_name} 뉴스 검색...")
    articles = _fetch_law_news(law_name)
    if articles:
        news_cache[law_name] = articles
        _save_news_cache(news_cache)
        print(f"  [News] {law_name}: {len(articles)}건")
    return articles


ANALYSIS_CACHE = DATA_DIR / "data-ai-analysis.json"


def _load_analysis_cache() -> dict:
    if ANALYSIS_CACHE.exists():
        return json.loads(ANALYSIS_CACHE.read_text(encoding="utf-8"))
    return {}


def _save_analysis_cache(cache: dict):
    ANALYSIS_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_law_analysis(law: dict, cache: dict) -> dict:
    """법령 분석 결과를 캐시에서 가져오거나 LLM으로 생성"""
    law_id = str(law["law_id"])
    if law_id in cache:
        return cache[law_id]

    try:
        from briefingroom.llm import analyze_law_change
    except Exception:
        return {}

    # 주요 조문 5개 + 개정이유를 LLM에 전달
    top_articles = []
    for art in law["articles"][:10]:
        if art["title"]:
            top_articles.append(f"제{art['no']}조 {art['title']}")

    payload = {
        "law_name": law["name"],
        "ministry": law["ministry"],
        "category": law["cat_label"],
        "enforcement_date": law["enforcement_date"],
        "promulgation_date": law["promulgation_date"],
        "amendment_reason": law["amendment_reason"][:300],
        "article_count": law["article_count"],
        "key_articles": top_articles[:8],
    }

    print(f"  [LLM] {law['name']} 분석 요청...")
    analysis = analyze_law_change(payload)

    if analysis.get("background"):
        cache[law_id] = analysis
        _save_analysis_cache(cache)
        print(f"  [LLM] {law['name']} 분석 완료")
    else:
        print(f"  [LLM] {law['name']} 분석 실패 (빈 결과)")

    return analysis


def _build_news_html(news: list[dict]) -> str:
    """관련 뉴스 HTML 생성"""
    if not news:
        return ""
    items = ""
    for n in news[:5]:
        items += f"""<a href="{h.escape(n.get('link',''))}" target="_blank" rel="noopener" style="display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-top:1px dashed var(--bl);text-decoration:none;color:var(--t);font-size:14px">
<span style="font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px;background:var(--sec-bg);color:var(--sec);flex-shrink:0;margin-top:2px">NEWS</span>
<span style="flex:1;font-weight:500;line-height:1.5">{h.escape(n.get('title',''))}</span>
<span style="font-size:11px;color:var(--t3);flex-shrink:0">{h.escape(n.get('source',''))}</span>
</a>\n"""
    return f"""<div class="sec-hdr">관련 뉴스</div>
<div style="background:#fff;border:1px solid var(--b);border-radius:10px;padding:14px 22px;margin-bottom:16px">{items}</div>"""


def generate_law_detail_page(law: dict, analysis: dict = None, news: list = None) -> Path:
    """개별 법령 상세 페이지 생성"""
    if analysis is None:
        analysis = {}
    if news is None:
        news = []
    law_id = law["law_id"]
    name = law["name"]
    cat_label = law["cat_label"]
    color, bg_color = CAT_COLORS.get(cat_label, ("#7c3aed", "#f5f3ff"))
    ministry = law["ministry"]
    articles = law["articles"]
    amendment = law["amendment_reason"]

    # 개정이유 정리 (불필요한 공포문 제거)
    if amendment:
        for cut in ["대통령", "국무총리", "(인)", "국무위원"]:
            idx = amendment.find(cut)
            if idx > 20:
                amendment = amendment[:idx].strip()
                break

    # 조문 HTML
    articles_html = ""
    for art in articles:
        title = h.escape(art["title"] or "")
        content = h.escape(art["content"] or "")
        content_formatted = content.replace("\n", "<br>")
        articles_html += f"""<div class="art-item" id="art-{h.escape(art['no'])}">
<div class="art-no">제{h.escape(art['no'])}조</div>
<div class="art-title">{title}</div>
<div class="art-content">{content_formatted}</div>
</div>\n"""

    out_dir = DATA_AI_DIR / "laws" / str(law_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{h.escape(name)} - 데이터/AI 규제 - 브리핑룸</title>
<meta name="description" content="{h.escape(name)} 조문 전문과 개정 이력. {h.escape(ministry)} 소관.">
<link rel="canonical" href="{SITE_URL}/regulation/data-ai/laws/{law_id}/">
<meta property="og:type" content="article">
<meta property="og:title" content="{h.escape(name)} - 브리핑룸">
<meta property="og:url" content="{SITE_URL}/regulation/data-ai/laws/{law_id}/">
<meta property="og:site_name" content="govbrief.kr">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<script>(function(){{if(/Mobi|Android|iPhone/i.test(navigator.userAgent))document.documentElement.classList.add('is-mobile')}})();</script>
<style>
{COMMON_CSS}
.hero{{background:linear-gradient(180deg,var(--sec-bg),#fff);border-bottom:1px solid var(--sec-border);padding:40px 32px 32px}}
.hero-inner{{max-width:1080px;margin:0 auto}}
.hero-bc{{font-size:12px;color:var(--t3);margin-bottom:14px}}
.hero-bc a{{color:var(--sec);text-decoration:none;font-weight:600}}
.hero-bc span{{margin:0 6px;color:var(--m)}}
.hero-badges{{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}}
.hero-badge{{font-family:var(--mono);font-size:12px;font-weight:700;padding:4px 10px;border-radius:4px;background:{bg_color};color:{color}}}
.hero-ministry{{font-size:14px;color:var(--t2);font-weight:600}}
.hero-title{{font-family:var(--serif);font-size:28px;font-weight:700;line-height:1.4;margin-bottom:10px}}
.hero-meta{{font-size:13px;color:var(--t3);display:flex;gap:16px;flex-wrap:wrap}}
.hero-meta span{{font-family:var(--mono)}}
.is-mobile .hero{{padding:24px 16px 20px}}
.is-mobile .hero-title{{font-size:22px}}
.shell{{max-width:1080px;margin:0 auto;padding:24px 16px 40px}}
.sec-hdr{{font-family:var(--serif);font-size:22px;font-weight:700;display:flex;align-items:center;gap:10px;margin:28px 0 14px}}
.sec-hdr:first-child{{margin-top:0}}
.sec-hdr::before{{content:'';width:3px;height:18px;background:var(--sec);border-radius:1px}}
.amend-box{{background:var(--sec-bg);border-left:4px solid var(--sec);border-radius:0 10px 10px 0;padding:18px 24px;margin-bottom:20px;font-size:15px;color:var(--t2);line-height:1.8}}
.art-item{{background:#fff;border:1px solid var(--b);border-radius:10px;padding:18px 22px;margin-bottom:8px}}
.art-no{{font-family:var(--mono);font-size:12px;font-weight:700;color:{color};margin-bottom:4px}}
.art-title{{font-family:var(--serif);font-size:16px;font-weight:700;margin-bottom:8px}}
.art-content{{font-size:14px;color:var(--t2);line-height:1.8}}
.bnav{{display:none}}.is-mobile .bnav{{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;bottom:0;left:0;right:0;z-index:200;background:#fff;border-top:1px solid var(--b);padding:8px 0 calc(10px + env(safe-area-inset-bottom))}}.bnav a{{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--t3);font-size:10.5px;font-weight:600}}.bnav a.on{{color:var(--sec)}}
</style>
</head>
<body>
{HEADER_HTML}
<section class="hero">
  <div class="hero-inner">
    <div class="hero-bc"><a href="/regulation/">규제</a><span>/</span><a href="/regulation/data-ai/">데이터/AI</a><span>/</span>{h.escape(name)}</div>
    <div class="hero-badges">
      <span class="hero-badge">{h.escape(cat_label)}</span>
      <span class="hero-badge" style="background:#f3f4f6;color:#6b7280">{h.escape(law['law_type'] or '법률')}</span>
      <span class="hero-ministry">{h.escape(ministry)}</span>
    </div>
    <h1 class="hero-title">{h.escape(name)}</h1>
    <div class="hero-meta">
      <span>조문 {len(articles)}개</span>
      <span>공포 {law['promulgation_date'][:4]}.{law['promulgation_date'][4:6]}.{law['promulgation_date'][6:]}</span>
      <span>시행 {law['enforcement_date'][:4]}.{law['enforcement_date'][4:6]}.{law['enforcement_date'][6:]}</span>
    </div>
  </div>
</section>
<div class="shell">
  {"<div class='sec-hdr'>최근 개정이유</div><div class='amend-box'>" + h.escape(amendment) + "</div>" if amendment and len(amendment) > 20 else ""}
  {_build_analysis_html(analysis, color)}
  {_build_news_html(news)}
  <div class="sec-hdr">조문 전문 ({len(articles)}개)</div>
  {articles_html}
</div>
{FOOTER_HTML}
</body>
</html>"""

    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return out_dir


def generate_timeline_page(laws: list[dict], analysis_cache: dict = None) -> Path:
    """타임라인 페이지 생성 (DB 데이터 기반)"""

    # 연도별 그룹핑
    by_year: dict[str, list] = {}
    for law in laws:
        ef = law["enforcement_date"]
        if not ef or len(ef) < 4:
            continue
        year = ef[:4]
        date_fmt = f"{ef[:4]}.{ef[4:6]}.{ef[6:]}"
        cat_label = law["cat_label"]
        dot_cls = {"데이터": "data", "인공지능": "ai", "디지털": "digital"}.get(cat_label, "data")
        badge_cls = {"데이터": "data", "인공지능": "ai", "디지털": "digital"}.get(cat_label, "data")

        # LLM 분석 + 뉴스 결과 가져오기
        law_analysis = (analysis_cache or {}).get(str(law["law_id"]), {})
        law_news = _load_news_cache().get(law["name"], [])

        entry = {
            "date": date_fmt,
            "cat": dot_cls,
            "badge_cls": badge_cls,
            "cat_label": cat_label,
            "name": law["name"],
            "ministry": law["ministry"].split(",")[0] if law["ministry"] else "",
            "amendment": law["amendment_reason"][:200] if law["amendment_reason"] else "",
            "article_count": law["article_count"],
            "law_id": law["law_id"],
            "analysis": law_analysis,
            "news": law_news[:3],
        }
        by_year.setdefault(year, []).append(entry)

    # 타임라인 HTML
    timeline_html = ""
    for year in sorted(by_year.keys(), reverse=True):
        timeline_html += f'<div class="tl-year">{year}</div>\n<div class="tl">\n'
        for entry in sorted(by_year[year], key=lambda x: x["date"], reverse=True):
            amend_text = entry["amendment"]
            # 불필요한 공포문 제거
            for cut in ["대통령", "국무총리", "(인)", "국무위원"]:
                idx = amend_text.find(cut)
                if idx > 20:
                    amend_text = amend_text[:idx].strip()
                    break

            amend_block = ""
            if amend_text and len(amend_text) > 20:
                amend_block = f'<div class="tl-card-body">{h.escape(amend_text)}</div>'

            # LLM 분석 블록
            analysis_block = ""
            a = entry.get("analysis", {})
            if a.get("background"):
                analysis_block += f'<div style="background:var(--sec-bg);border-left:3px solid var(--sec);border-radius:0 8px 8px 0;padding:12px 16px;margin:8px 0;font-size:14px;color:var(--t2);line-height:1.8"><div style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--sec);margin-bottom:4px">개정 배경</div>{h.escape(a["background"])}</div>'
            if a.get("impact"):
                analysis_block += f'<div style="border-left:3px solid #d97706;background:#fef3c7;border-radius:0 8px 8px 0;padding:12px 16px;margin:8px 0;font-size:14px;color:var(--t2);line-height:1.8"><div style="font-family:var(--mono);font-size:10px;font-weight:700;color:#d97706;margin-bottom:4px">실무 영향</div>{h.escape(a["impact"])}</div>'
            if a.get("target"):
                analysis_block += f'<div style="font-size:13px;color:var(--t3);margin-top:6px"><strong style="color:var(--t2)">영향 대상:</strong> {h.escape(a["target"])}</div>'

            # 키워드 태그
            kw_block = ""
            kws = a.get("keywords", [])
            if kws:
                kw_block = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:8px">' + "".join(f'<span style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;border:1px solid var(--sec-border);color:var(--sec)">{h.escape(kw)}</span>' for kw in kws) + '</div>'

            timeline_html += f"""<div class="tl-entry" data-cat="{entry['cat']}">
<div class="tl-dot tl-dot-{entry['cat']}"></div>
<div class="tl-card">
<div class="tl-card-top">
  <span class="tl-date">{entry['date']} 시행</span>
  <span class="tl-badge tl-badge-{entry['badge_cls']}">{h.escape(entry['cat_label'])}</span>
  <span class="tl-ministry">{h.escape(entry['ministry'])}</span>
</div>
<div class="tl-card-title"><a href="/regulation/data-ai/laws/{entry['law_id']}/" style="color:var(--t);text-decoration:none">{h.escape(entry['name'])}</a></div>
{amend_block}
{analysis_block}
{kw_block}
{"".join(f'<a href="{h.escape(n.get("link",""))}" target="_blank" rel="noopener" style="display:flex;align-items:center;gap:6px;margin-top:6px;font-size:12px;color:var(--t2);text-decoration:none"><span style="font-family:var(--mono);font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;background:var(--sec-bg);color:var(--sec)">NEWS</span>{h.escape(n.get("title","")[:50])}<span style="color:var(--t3);margin-left:auto">{h.escape(n.get("source",""))}</span></a>' for n in entry.get("news", [])[:2])}
<div style="display:flex;align-items:center;gap:12px;margin-top:10px">
  <span style="font-family:var(--mono);font-size:12px;color:var(--sec);font-weight:700">조문 {entry['article_count']}개</span>
  <a href="/regulation/data-ai/laws/{entry['law_id']}/" style="font-size:13px;color:var(--sec);font-weight:600;text-decoration:none">조문 전문 + 상세 분석 보기 &#8594;</a>
</div>
</div>
</div>\n"""
        timeline_html += "</div>\n"

    tl_dir = DATA_AI_DIR / "timeline"
    tl_dir.mkdir(parents=True, exist_ok=True)

    # 타임라인 페이지 CSS는 목업에서 가져옴
    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>데이터/AI 규제 변화 타임라인 - 브리핑룸</title>
<meta name="description" content="개인정보보호법, AI기본법, 데이터3법 등 데이터/인공지능 관련 법령의 개정 이력을 시간순으로 추적합니다.">
<link rel="canonical" href="{SITE_URL}/regulation/data-ai/timeline/">
<meta property="og:type" content="website">
<meta property="og:title" content="데이터/AI 규제 변화 타임라인 - 브리핑룸">
<meta property="og:url" content="{SITE_URL}/regulation/data-ai/timeline/">
<meta property="og:site_name" content="govbrief.kr">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<script>(function(){{if(/Mobi|Android|iPhone/i.test(navigator.userAgent))document.documentElement.classList.add('is-mobile')}})();</script>
<style>
{COMMON_CSS}
.hero{{background:linear-gradient(180deg,var(--sec-bg),#fff);border-bottom:1px solid var(--sec-border);padding:40px 32px 32px}}
.hero-inner{{max-width:1080px;margin:0 auto}}
.hero-bc{{font-size:12px;color:var(--t3);margin-bottom:14px}}
.hero-bc a{{color:var(--sec);text-decoration:none;font-weight:600}}
.hero-bc span{{margin:0 6px;color:var(--m)}}
.hero-ey{{font-family:var(--mono);font-size:11px;color:var(--sec);font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px}}
.hero-title{{font-family:var(--serif);font-size:30px;font-weight:700;margin-bottom:6px}}
.hero-sub{{font-size:15px;color:var(--t2);line-height:1.7;max-width:700px}}
.is-mobile .hero{{padding:24px 16px 20px}}
.is-mobile .hero-title{{font-size:22px}}
.shell{{max-width:1080px;margin:0 auto;padding:24px 16px 40px}}
.tl-filter{{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap}}
.tl-fbtn{{font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;border:1px solid var(--b);background:#fff;color:var(--t2);cursor:pointer}}
.tl-fbtn:hover{{border-color:var(--sec);color:var(--sec)}}
.tl-fbtn.on{{background:var(--sec);color:#fff;border-color:var(--sec)}}
.tl-year{{font-family:var(--mono);font-size:28px;font-weight:700;color:var(--sec);margin:32px 0 16px;padding-bottom:8px;border-bottom:2px solid var(--sec-border)}}
.tl-year:first-child{{margin-top:0}}
.tl{{position:relative;padding-left:32px}}
.tl::before{{content:'';position:absolute;left:11px;top:0;bottom:0;width:2px;background:var(--bl)}}
.tl-entry{{position:relative;margin-bottom:20px}}
.tl-dot{{position:absolute;left:-32px;top:8px;width:22px;height:22px;border-radius:50%;border:3px solid #fff;box-shadow:0 0 0 2px var(--sec)}}
.tl-dot-data{{background:var(--data)}}
.tl-dot-ai{{background:var(--ai)}}
.tl-dot-digital{{background:var(--digital)}}
.tl-card{{background:#fff;border:1px solid var(--b);border-radius:10px;padding:20px 24px}}
.tl-card:hover{{box-shadow:0 2px 12px rgba(0,0,0,.06)}}
.tl-card-top{{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}}
.tl-date{{font-family:var(--mono);font-size:13px;font-weight:700;color:var(--sec)}}
.tl-badge{{font-family:var(--mono);font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px}}
.tl-badge-data{{background:var(--data-bg);color:var(--data)}}
.tl-badge-ai{{background:var(--ai-bg);color:var(--ai)}}
.tl-badge-digital{{background:var(--digital-bg);color:var(--digital)}}
.tl-ministry{{font-size:12px;color:var(--t3);margin-left:auto}}
.tl-card-title{{font-family:var(--serif);font-size:18px;font-weight:700;line-height:1.4;margin-bottom:8px}}
.tl-card-title a:hover{{color:var(--sec)}}
.tl-card-body{{font-size:14px;color:var(--t2);line-height:1.8}}
.bnav{{display:none}}.is-mobile .bnav{{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;bottom:0;left:0;right:0;z-index:200;background:#fff;border-top:1px solid var(--b);padding:8px 0 calc(10px + env(safe-area-inset-bottom))}}.bnav a{{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--t3);font-size:10.5px;font-weight:600}}.bnav a.on{{color:var(--sec)}}
</style>
</head>
<body>
{HEADER_HTML}
<section class="hero">
  <div class="hero-inner">
    <div class="hero-bc"><a href="/regulation/">규제</a><span>/</span><a href="/regulation/data-ai/">데이터/AI</a><span>/</span>타임라인</div>
    <div class="hero-ey">REGULATION CHANGE TIMELINE</div>
    <h1 class="hero-title">데이터/AI 규제 변화 타임라인</h1>
    <p class="hero-sub">14개 법령의 개정 이력을 시간순으로 추적합니다. 각 항목을 클릭하면 조문 전문을 확인할 수 있습니다.</p>
  </div>
</section>
<div class="shell">
  <div class="tl-filter">
    <span class="tl-fbtn on" data-f="all">전체</span>
    <span class="tl-fbtn" data-f="data">개인정보/데이터</span>
    <span class="tl-fbtn" data-f="ai">인공지능</span>
    <span class="tl-fbtn" data-f="digital">디지털/플랫폼</span>
  </div>
  {timeline_html}
</div>
{FOOTER_HTML}
<script>
document.querySelector('.tl-filter').addEventListener('click',function(e){{
  var btn=e.target.closest('.tl-fbtn');if(!btn)return;
  this.querySelectorAll('.tl-fbtn').forEach(function(b){{b.classList.remove('on')}});
  btn.classList.add('on');
  var cat=btn.dataset.f;
  document.querySelectorAll('.tl-entry').forEach(function(entry){{
    entry.style.display=(cat==='all'||entry.dataset.cat===cat)?'':'none';
  }});
}});
</script>
</body>
</html>"""

    (tl_dir / "index.html").write_text(page, encoding="utf-8")
    print(f"  [Timeline] regulation/data-ai/timeline/index.html 생성 ({len(laws)}건)")
    return tl_dir


def main():
    if not DB_PATH.exists():
        print("[data-ai-pages] DB 없음 - 스킵")
        return

    conn = sqlite3.connect(str(DB_PATH))
    laws = _get_data_ai_laws(conn)
    conn.close()

    if not laws:
        print("[data-ai-pages] 데이터/AI 법령 없음 - 스킵")
        return

    print(f"[data-ai-pages] {len(laws)}개 법령 처리 시작")

    # LLM 분석 캐시 로드
    cache = _load_analysis_cache()
    news_cache = _load_news_cache()

    # 1. LLM 분석 (캐시에 없는 것만)
    for law in laws:
        if law["article_count"] > 0 and str(law["law_id"]) not in cache:
            _get_law_analysis(law, cache)
            _time.sleep(1)

    # 2. 뉴스 크롤링 (캐시에 없는 것만, 본법만)
    for law in laws:
        if "시행령" not in law["name"] and "시행규칙" not in law["name"]:
            if law["name"] not in news_cache:
                _get_law_news(law["name"], news_cache)
                _time.sleep(0.5)

    # 3. 법령 상세 페이지
    for law in laws:
        if law["article_count"] > 0:
            analysis = cache.get(str(law["law_id"]), {})
            news = news_cache.get(law["name"], [])
            generate_law_detail_page(law, analysis, news)
            has_analysis = "+" if analysis.get("background") else "-"
            has_news = f"{len(news)}건" if news else "-"
            print(f"  [Law] {law['name']}: 조문 {law['article_count']}개 [LLM:{has_analysis}] [뉴스:{has_news}]")

    # 3. 타임라인 페이지 (본법만, 시행령 제외)
    main_laws = [l for l in laws if "시행령" not in l["name"] and "시행규칙" not in l["name"]]
    generate_timeline_page(main_laws, cache)

    print(f"[data-ai-pages] 완료: 법령 상세 {sum(1 for l in laws if l['article_count'] > 0)}개 + 타임라인 1개")


if __name__ == "__main__":
    main()
