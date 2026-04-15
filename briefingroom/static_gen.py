"""정적 사이트 생성기 — RSS 피드 + 개별 기사 HTML 생성"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

from briefingroom.config import DATA_DIR
from briefingroom.finlaw_pages import generate_cases_page, generate_finlaw_index, generate_notices_page
from briefingroom.home_gen import generate_home, generate_policy_page
from briefingroom.site_templates import (
    SITE_BASE_CSS, SITE_FONT_LINKS, SITE_NAV_CSS,
    render_bottom_nav, render_crosslinks, render_footer, render_top_nav,
)

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


def _build_easy_summary(easy: str) -> str:
    if not easy or not easy.strip():
        return ""
    text = easy.strip().replace("\n", " ")
    return f"""<section style="background:var(--al);border:2px solid var(--ab);border-radius:12px;padding:18px;margin-bottom:18px">
      <div style="font-size:10px;font-weight:700;color:var(--a);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">한눈에 보기</div>
      <p style="font-size:14px;color:var(--t);line-height:1.8;margin:0">{html.escape(text)}</p>
    </section>"""


def _build_original_link(url: str) -> str:
    return f"""<div class="links">
      <h4>원문</h4>
      <a href="{url or '#'}" target="_blank" rel="noopener noreferrer">원문 보기 →</a>
    </div>"""


def generate_rss(target_date: str, max_items: int = 50) -> Path:
    """최근 일별 JSON들을 합산하여 RSS 2.0 XML 생성 (최대 50건)

    target_date부터 역순으로 최대 14일치 JSON을 읽어 최신 기사 50건을 포함합니다.
    """
    from datetime import timedelta

    # 최근 14일치 JSON에서 기사 수집 (최신순)
    all_articles = []
    base_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    for delta in range(14):
        d = base_date - timedelta(days=delta)
        json_path = DATA_DIR / f"{d.isoformat()}.json"
        if not json_path.exists():
            continue
        data = json.loads(json_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        for idx, it in enumerate(items):
            it["_rss_date"] = d.isoformat()
            it["_rss_idx"] = idx
            all_articles.append(it)
        if len(all_articles) >= max_items:
            break

    if not all_articles:
        print(f"  [RSS] 최근 14일간 JSON 없음 → 스킵")
        return None

    all_articles = all_articles[:max_items]

    rss_items = []
    for it in all_articles:
        title = xml_escape(it.get("title", ""))
        source = xml_escape(it.get("source", ""))
        summary = xml_escape(it.get("summary", ""))
        date_str = it.get("date", it["_rss_date"])
        idx = it["_rss_idx"]
        category = xml_escape(it.get("category", ""))
        keywords = it.get("keywords", [])
        kw_html = " ".join(f"#{xml_escape(k)}" for k in keywords) if keywords else ""

        pub_date = datetime.strptime(date_str, "%Y-%m-%d").strftime(
            "%a, %d %b %Y 09:00:00 +0900"
        )

        slug = it.get("slug") or f"{idx:03d}"
        article_link = f"{SITE_URL}/articles/{date_str}/{slug}/"

        description = f"[{source}] {summary}" if summary else f"[{source}] {title}"
        if kw_html:
            description += f" | {kw_html}"

        rss_items.append(f"""    <item>
      <title>{title}</title>
      <link>{article_link}</link>
      <guid isPermaLink="true">{article_link}</guid>
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
    print(f"  [RSS] {out_path} 생성 ({len(rss_items)}건, 최근 {len(set(it['_rss_date'] for it in all_articles))}일치)")
    return out_path


def _find_related_articles(current_idx: int, items: list[dict], max_results: int = 4) -> list[dict]:
    """키워드 기반으로 관련 보도자료를 찾는다."""
    current = items[current_idx]
    current_kws = set(current.get("keywords", []))
    if not current_kws:
        return []

    scored = []
    for idx, it in enumerate(items):
        if idx == current_idx:
            continue
        other_kws = set(it.get("keywords", []))
        overlap = len(current_kws & other_kws)
        if overlap > 0:
            scored.append((overlap, idx))

    scored.sort(key=lambda x: -x[0])
    return [items[i] for _, i in scored[:max_results]]


DATA_AI_KEYWORDS = {
    "개인정보": ("개인정보 보호법", "/regulation/data-ai/laws/000751/"),
    "마이데이터": ("신용정보의 이용 및 보호에 관한 법률", "/regulation/data-ai/laws/009199/"),
    "신용정보": ("신용정보의 이용 및 보호에 관한 법률", "/regulation/data-ai/laws/009199/"),
    "인공지능": ("지능정보화 기본법", "/regulation/data-ai/laws/000028/"),
    "AI": ("지능정보화 기본법", "/regulation/data-ai/laws/000028/"),
    "데이터": ("데이터 산업진흥 및 이용촉진에 관한 기본법", "/regulation/data-ai/laws/014168/"),
    "클라우드": ("클라우드컴퓨팅 발전 및 이용자 보호에 관한 법률", "/regulation/data-ai/laws/012266/"),
    "소프트웨어": ("소프트웨어 진흥법", "/regulation/data-ai/laws/001733/"),
    "전자정부": ("전자정부법", "/regulation/data-ai/laws/001734/"),
    "정보통신": ("정보통신망법", "/regulation/data-ai/laws/002000/"),
    "정보보호": ("정보통신망법", "/regulation/data-ai/laws/002000/"),
    "전자서명": ("전자서명법", "/regulation/data-ai/laws/001540/"),
    "위치정보": ("위치정보법", "/regulation/data-ai/laws/009882/"),
    "전자금융": ("전자금융거래법", "/regulation/data-ai/laws/009413/"),
    "가상자산": ("전자금융거래법", "/regulation/data-ai/laws/009413/"),
    "전자문서": ("전자문서 및 전자거래 기본법", "/regulation/data-ai/laws/000030/"),
    "알고리즘": ("지능정보화 기본법", "/regulation/data-ai/laws/000028/"),
    "가명정보": ("개인정보 보호법", "/regulation/data-ai/laws/000751/"),
}


def _find_related_regulations(keywords: list[str], category: str) -> list[dict]:
    """보도자료 키워드로 관련 규제 법령을 찾는다."""
    results = []
    seen = set()

    # 데이터/AI 키워드 매칭
    for kw in keywords:
        for trigger, (law_name, link) in DATA_AI_KEYWORDS.items():
            if trigger in kw and law_name not in seen:
                results.append({"law_name": law_name, "detail_link": link, "description": f"데이터/AI 규제"})
                seen.add(law_name)
                if len(results) >= 3:
                    break
        if len(results) >= 3:
            break

    # 금융경제 카테고리면 regulation-stats.json도 활용
    if category == "금융경제" and len(results) < 3:
        stats_path = DATA_DIR / "regulation-stats.json"
        if stats_path.exists():
            try:
                stats = json.loads(stats_path.read_text(encoding="utf-8"))
                for r in stats.get("recent_changes", [])[:3]:
                    name = r.get("name", "")
                    if name and name not in seen:
                        results.append({"law_name": name, "detail_link": r.get("link", ""), "description": r.get("desc", "")})
                        seen.add(name)
                        if len(results) >= 3:
                            break
            except Exception:
                pass

    return results[:3]


def _build_reg_links(keywords: list[str]) -> str:
    """키워드 기반 관련 규제 법령 링크 생성"""
    regs = _find_related_regulations(keywords, "")
    if not regs:
        return ""
    items = ""
    for r in regs:
        link = r.get("detail_link", "")
        if not link:
            continue
        items += f'<a href="{html.escape(link)}" style="display:flex;align-items:center;gap:8px;padding:8px 0;border-top:1px dashed var(--bl);text-decoration:none;color:var(--t);font-size:14px"><span style="font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px;background:var(--sec-bg);color:var(--sec);flex-shrink:0">법령</span><span style="flex:1;font-weight:600">{html.escape(r.get("law_name",""))}</span><span style="font-size:12px;color:var(--sec);font-weight:600">조문 보기 &#8594;</span></a>'
    if not items:
        return ""
    return f'<div style="background:#fff;border:1px solid var(--b);border-radius:10px;padding:14px 22px;margin-bottom:16px"><div style="font-family:var(--serif);font-size:16px;font-weight:700;margin-bottom:8px;display:flex;align-items:center;gap:8px"><span style="width:3px;height:14px;background:var(--sec);border-radius:1px;display:inline-block"></span>관련 규제 법령</div>{items}</div>'


def _build_key_points_html(points: list[str]) -> str:
    if not points:
        return ""
    rows = ""
    for i, p in enumerate(points, 1):
        # "제목 - 설명" 형식 파싱
        if " - " in p:
            title_part, desc_part = p.split(" - ", 1)
            text = f"<strong>{html.escape(title_part.strip())}</strong> - {html.escape(desc_part.strip())}"
        else:
            text = html.escape(p)
        rows += f'<div class="pt-item"><span class="pt-num">{i:02d}</span><div class="pt-text">{text}</div></div>\n'
    return f'<div class="points-box"><div class="sec-title">핵심 포인트</div>{rows}</div>'


def _build_detailed_analysis_html(analysis: str) -> str:
    if not analysis or not analysis.strip():
        return ""
    paragraphs = [p.strip() for p in analysis.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in analysis.split("\n") if p.strip()]
    body = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    return f'<div class="analysis-box"><div class="sec-title">상세 분석</div><div class="analysis-text">{body}</div></div>'


def _build_related_articles_html(related: list[dict], target_date: str) -> str:
    if not related:
        return ""
    rows = ""
    for r in related:
        imp = r.get("impact", "중")
        imp_cls = "ri-h" if imp == "상" else ("ri-m" if imp == "중" else "ri-l")
        slug = r.get("slug", "000")
        date = r.get("date", target_date)
        rows += f'''<div class="rel-item">
<a href="/articles/{date}/{slug}/"><span class="rel-imp {imp_cls}">{html.escape(imp)}</span>{html.escape(r.get("title", ""))}</a>
<div class="rel-meta">{html.escape(r.get("source", ""))} / {date}</div></div>\n'''
    return f'<div class="related-box"><div class="sb-title">관련 보도자료</div>{rows}</div>'


def _build_sidebar_meta_html(it: dict) -> str:
    imp = it.get("impact", "중")
    return f'''<div class="meta-box"><div class="sb-title">보도자료 정보</div>
<div class="mb-row"><span class="mb-label">발표 부처</span><span class="mb-val">{html.escape(it.get("source", ""))}</span></div>
<div class="mb-row"><span class="mb-label">발표일</span><span class="mb-val">{html.escape(it.get("date", ""))}</span></div>
<div class="mb-row"><span class="mb-label">분야</span><span class="mb-val">{html.escape(it.get("category", ""))}</span></div>
<div class="mb-row"><span class="mb-label">영향도</span><span class="mb-val mb-imp">{html.escape(imp)}</span></div></div>'''


ARTICLE_DETAIL_CSS = """
*{box-sizing:border-box;margin:0;padding:0;word-break:keep-all}
:root{--a:#d96c2c;--al:rgba(217,108,44,.06);--bg:#f7f7f5;--s:#fff;--s2:#fafaf8;--b:#dcdcd8;--bl:#ededea;--t:#1a1a1a;--t2:#555;--t3:#888;--m:#bbb;--sec:#1e40af;--sec-bg:#eff6ff;--sec-border:#bfdbfe;--red:#dc2626;--red-bg:#fee2e2;--amber:#d97706;--amber-bg:#fef3c7;--green:#047857;--green-bg:#ecfdf5;--purple:#7c3aed;--purple-bg:#f5f3ff;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}
body{background:var(--bg);color:var(--t);font-family:var(--sans);font-size:17px;line-height:1.7;min-width:1120px}
.is-mobile body{min-width:0;font-size:16px;padding-bottom:68px}
.hdr{background:#fff;border-bottom:1px solid var(--b);height:64px;display:flex;align-items:center;padding:0 32px;position:sticky;top:0;z-index:100}
.hdr-logo{font-family:var(--serif);font-size:24px;font-weight:700;color:var(--t);text-decoration:none;margin-right:44px}
.hdr-nav{display:flex;gap:6px;flex:1}
.hdr-nav a{font-size:15px;font-weight:600;color:var(--t2);text-decoration:none;padding:10px 16px;border-radius:6px}
.hdr-nav a:hover{background:var(--bl)}
.hdr-nav a.on{color:var(--sec);background:var(--sec-bg);font-weight:700}
.hdr-nav .lbl-short{display:none}
.is-mobile .hdr{height:52px;padding:0 12px}
.is-mobile .hdr-logo{font-size:17px;margin-right:8px}
.is-mobile .hdr-nav a{font-size:12px;padding:7px 8px}
.is-mobile .hdr-nav .lbl-full{display:none}
.is-mobile .hdr-nav .lbl-short{display:inline}
.hero{background:linear-gradient(180deg,var(--sec-bg),#fff);border-bottom:1px solid var(--sec-border);padding:40px 32px 32px}
.hero-inner{max-width:1080px;margin:0 auto}
.hero-bc{font-size:13px;color:var(--t3);margin-bottom:14px}
.hero-bc a{color:var(--sec);text-decoration:none;font-weight:600}
.hero-bc span{margin:0 6px;color:var(--m)}
.hero-badges{display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap}
.hero-imp{font-family:var(--mono);font-size:12px;font-weight:700;padding:5px 12px;border-radius:4px}
.hero-imp-h{background:var(--red-bg);color:var(--red)}
.hero-imp-m{background:var(--amber-bg);color:var(--amber)}
.hero-imp-l{background:#f3f4f6;color:#6b7280}
.hero-cat{font-size:13px;font-weight:600;padding:4px 10px;border-radius:4px;color:var(--sec);background:var(--sec-bg)}
.hero-source{font-size:14px;font-weight:600;color:var(--t2)}
.hero-date{font-family:var(--mono);font-size:13px;color:var(--t3)}
.hero-title{font-family:var(--serif);font-size:32px;font-weight:700;line-height:1.4;margin-bottom:16px;max-width:860px}
.hero-kws{display:flex;gap:8px;flex-wrap:wrap}
.hero-kw{font-size:13px;font-weight:600;padding:5px 12px;border-radius:10px;border:1px solid var(--sec-border);color:var(--sec)}
.is-mobile .hero{padding:24px 16px 20px}
.is-mobile .hero-title{font-size:23px}
.shell{max-width:1080px;margin:0 auto;padding:24px 16px 40px}
.easy-box{background:var(--sec-bg);border-left:4px solid var(--sec);border-radius:0 10px 10px 0;padding:20px 24px;margin-bottom:16px}
.easy-label{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--sec);letter-spacing:.06em;margin-bottom:6px}
.easy-text{font-size:16px;color:var(--t);line-height:1.9}
.sec-title{font-family:var(--serif);font-size:22px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:10px}
.sec-title::before{content:'';width:3px;height:18px;background:var(--sec);border-radius:1px}
.points-box{background:#fff;border:1px solid var(--b);border-radius:10px;padding:24px 28px;margin-bottom:16px}
.pt-item{display:flex;align-items:flex-start;gap:12px;padding:12px 0;border-top:1px dashed var(--bl)}
.pt-item:first-of-type{border-top:none}
.pt-num{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--sec);background:var(--sec-bg);border-radius:4px;padding:3px 8px;flex-shrink:0;margin-top:3px}
.pt-text{font-size:15px;color:var(--t);line-height:1.8}
.pt-text strong{font-weight:700}
.analysis-box{background:#fff;border:1px solid var(--b);border-radius:10px;padding:24px 28px;margin-bottom:16px}
.analysis-text{font-size:15px;color:var(--t2);line-height:1.9}
.analysis-text p{margin-bottom:14px}
.analysis-text p:last-child{margin-bottom:0}
.context-box{background:#fff;border:1px solid var(--b);border-radius:10px;padding:24px 28px;margin-bottom:16px}
.ctx-section{margin-bottom:14px}
.ctx-section:last-child{margin-bottom:0}
.ctx-label{font-family:var(--sans);font-size:15px;font-weight:700;letter-spacing:.02em;margin-bottom:8px}
.ctx-label-why{color:var(--sec)}
.ctx-label-impact{color:var(--amber)}
.ctx-label-who{color:var(--green)}
.ctx-body{border-left:4px solid var(--sec);background:var(--sec-bg);border-radius:0 10px 10px 0;padding:18px 24px;font-size:17px;color:var(--t);line-height:1.9}
.ctx-body-impact{border-left-color:var(--amber);background:var(--amber-bg)}
.ctx-body-who{border-left-color:var(--green);background:var(--green-bg)}
.kw-box{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}
.kw-tag{font-size:13px;font-weight:600;padding:5px 12px;border-radius:10px;border:1px solid var(--sec-border);color:var(--sec)}
.attach-box{background:#fff;border:1px solid var(--b);border-radius:10px;padding:20px 28px;margin-bottom:16px}
.attach-item{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px dashed var(--bl);font-size:14px}
.attach-item:first-of-type{border-top:none}
.attach-badge{font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;flex-shrink:0}
.attach-badge-pdf{background:var(--red-bg);color:var(--red)}
.attach-badge-hwp{background:var(--sec-bg);color:var(--sec)}
.attach-link{color:var(--t);text-decoration:none;font-weight:500}
.attach-link:hover{color:var(--sec)}
.related-box{background:#fff;border:1px solid var(--b);border-radius:10px;padding:20px 28px;margin-bottom:16px}
.rel-item{display:flex;align-items:flex-start;gap:8px;padding:10px 0;border-top:1px dashed var(--bl)}
.rel-item:first-of-type{border-top:none}
.rel-imp{font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px;flex-shrink:0;margin-top:3px}
.ri-h{background:var(--red-bg);color:var(--red)}
.ri-m{background:var(--amber-bg);color:var(--amber)}
.ri-l{background:#f3f4f6;color:#6b7280}
.rel-content{flex:1}
.rel-link{font-size:15px;color:var(--t);text-decoration:none;font-weight:600;line-height:1.5;display:block}
.rel-link:hover{color:var(--sec)}
.rel-meta{font-size:12px;color:var(--t3);margin-top:2px}
.source-box{background:#fff;border:1px solid var(--b);border-radius:10px;padding:18px 28px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between}
.source-info{font-size:15px;color:var(--t2)}
.source-info strong{color:var(--t);font-weight:700}
.source-link{font-size:14px;font-weight:700;color:var(--sec);text-decoration:none;padding:8px 18px;border:1px solid var(--sec-border);border-radius:6px}
.source-link:hover{background:var(--sec-bg)}
.nav-box{display:flex;gap:12px;margin-top:16px}
.nav-prev,.nav-next{flex:1;background:#fff;border:1px solid var(--b);border-radius:10px;padding:18px 22px;text-decoration:none;color:var(--t)}
.nav-prev:hover,.nav-next:hover{border-color:var(--sec);box-shadow:0 2px 8px rgba(0,0,0,.04)}
.nav-label{font-size:12px;color:var(--t3);font-weight:600;margin-bottom:6px}
.nav-title{font-family:var(--serif);font-size:15px;font-weight:700;line-height:1.4}
.nav-next{text-align:right}
.footer{max-width:1080px;margin:20px auto 0;padding:24px 16px;text-align:center;color:var(--t3);border-top:1px solid var(--bl)}
.footer-motto{font-family:var(--serif);font-size:14px;color:var(--t2)}
.footer-site{font-family:var(--mono);font-size:11px;color:var(--t3);margin-top:4px}
.bnav{display:none}
.is-mobile .bnav{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;bottom:0;left:0;right:0;z-index:200;background:#fff;border-top:1px solid var(--b);padding:8px 0 calc(10px + env(safe-area-inset-bottom))}
.bnav a{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--t3);font-size:10.5px;font-weight:600}
.bnav a.on{color:var(--sec)}
"""


def generate_article_pages(target_date: str) -> int:
    """개별 기사 정적 HTML 생성 (새 디자인 - 히어로 + 2컬럼)"""
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
        easy_summary = it.get("easy_summary", "")
        why_important = it.get("why_important", "")
        practical_impact = it.get("practical_impact", "")
        key_points = it.get("key_points", [])
        detailed_analysis = it.get("detailed_analysis", "")
        url = _safe_url(it.get("url", ""))
        date_str = it.get("date", target_date)
        category = it.get("category", "")
        impact = it.get("impact", "중")
        keywords = it.get("keywords", [])

        slug = it.get("slug") or f"{idx:03d}"
        article_url = f"{SITE_URL}/articles/{target_date}/{slug}/"
        kw_json = json.dumps(keywords, ensure_ascii=False)
        h_title = html.escape(title)
        h_source = html.escape(source)
        desc = f"[{source}] {summary[:120]}" if summary else f"[{source}] {title}"
        h_desc = html.escape(desc)

        # 영향도 CSS 클래스
        imp_cls = "hero-imp-h" if impact == "상" else ("hero-imp-m" if impact == "중" else "hero-imp-l")

        # 키워드 태그
        kw_tags = "".join(f'<span class="hero-kw">#{html.escape(k)}</span>' for k in keywords)

        # 쉬운 요약
        easy_html = ""
        # 쉬운요약이 없으면 일반 요약을 대신 사용
        easy_text = easy_summary.strip() if easy_summary and easy_summary.strip() else summary.strip()
        if easy_text:
            easy_html = f'<div class="easy-box"><div class="easy-label">EASY SUMMARY</div><div class="easy-text">{html.escape(easy_text)}</div></div>'

        # 핵심 포인트
        points_html = _build_key_points_html(key_points)

        # 상세 분석
        analysis_html = _build_detailed_analysis_html(detailed_analysis)

        # 왜 알아야 하나 / 뭐가 달라지나 / 누구에게 영향
        context_html = ""
        if why_important or practical_impact:
            ctx_inner = ""
            if why_important:
                ctx_inner += f'<div class="ctx-section"><div class="ctx-label ctx-label-why">WHY IT MATTERS - 왜 알아야 하나</div><div class="ctx-body">{html.escape(why_important.strip())}</div></div>'
            if practical_impact:
                ctx_inner += f'<div class="ctx-section"><div class="ctx-label ctx-label-impact">WHAT CHANGES - 그래서 뭐가 달라지나</div><div class="ctx-body ctx-body-impact">{html.escape(practical_impact.strip())}</div></div>'
            # 영향 대상 자동 추론 (카테고리 기반)
            who_map = {"금융경제": "금융기관, 투자자, 기업, 자영업자", "사회복지": "일반 국민, 취약계층, 복지 수급자", "산업기술": "관련 산업 종사자, 기업, 연구기관", "외교안보": "해외 체류 국민, 수출입 기업, 방위산업", "행정법제": "공무원, 행정서비스 이용자, 지방자치단체"}
            who = who_map.get(category, "")
            if who:
                ctx_inner += f'<div class="ctx-section"><div class="ctx-label ctx-label-who">WHO IS AFFECTED - 영향 대상</div><div class="ctx-body ctx-body-who">{html.escape(who)}</div></div>'
            context_html = f'<div class="context-box"><div class="sec-title">영향 분석</div>{ctx_inner}</div>'

        # 키워드 박스
        kw_box_html = ""
        if keywords:
            kw_box_html = '<div class="kw-box">' + "".join(f'<span class="kw-tag">#{html.escape(k)}</span>' for k in keywords) + '</div>'

        # 첨부파일
        attach_html = ""
        pdfs = it.get("pdfs", [])
        hwps = it.get("hwps", [])
        if pdfs or hwps:
            attach_inner = ""
            for i, p in enumerate(pdfs):
                attach_inner += f'<div class="attach-item"><span class="attach-badge attach-badge-pdf">PDF</span><a class="attach-link" href="{html.escape(p)}" target="_blank" rel="noopener">첨부파일 {i+1} (PDF)</a></div>'
            for i, h in enumerate(hwps):
                attach_inner += f'<div class="attach-item"><span class="attach-badge attach-badge-hwp">HWP</span><a class="attach-link" href="{html.escape(h)}" target="_blank" rel="noopener">첨부파일 {i+1} (HWP)</a></div>'
            attach_html = f'<div class="attach-box"><div class="sec-title">첨부파일</div>{attach_inner}</div>'

        # 관련 보도자료
        related = _find_related_articles(idx, items)
        related_html = ""
        if related:
            rel_inner = ""
            for r in related:
                rimp = r.get("impact", "중")
                ricls = "ri-h" if rimp == "상" else ("ri-m" if rimp == "중" else "ri-l")
                rslug = r.get("slug", "000")
                rel_inner += f'<div class="rel-item"><span class="rel-imp {ricls}">{html.escape(rimp)}</span><div class="rel-content"><a class="rel-link" href="/articles/{target_date}/{rslug}/">{html.escape(r.get("title","")[:60])}</a><div class="rel-meta">{html.escape(r.get("source",""))} / {html.escape(r.get("category",""))}</div></div></div>'
            related_html = f'<div class="related-box"><div class="sec-title">관련 보도자료</div>{rel_inner}</div>'

        # 원문 링크
        source_html = ""
        if url:
            source_html = f'<div class="source-box"><div class="source-info"><strong>{h_source}</strong> 보도자료 원문</div><a class="source-link" href="{url}" target="_blank" rel="noopener">원문 보기 &#8594;</a></div>'

        # 이전/다음
        nav_html = '<div class="nav-box">'
        if idx > 0:
            prev_it = items[idx - 1]
            prev_slug = prev_it.get("slug") or f"{idx-1:03d}"
            nav_html += f'<a class="nav-prev" href="/articles/{target_date}/{prev_slug}/"><div class="nav-label">이전 보도자료</div><div class="nav-title">{html.escape(prev_it.get("title", "")[:50])}</div></a>'
        else:
            nav_html += f'<a class="nav-prev" href="/brief/articles/"><div class="nav-label">목록으로</div><div class="nav-title">오늘의 정부 발표</div></a>'
        if idx < len(items) - 1:
            next_it = items[idx + 1]
            next_slug = next_it.get("slug") or f"{idx+1:03d}"
            nav_html += f'<a class="nav-next" href="/articles/{target_date}/{next_slug}/"><div class="nav-label">다음 보도자료</div><div class="nav-title">{html.escape(next_it.get("title", "")[:50])}</div></a>'
        else:
            nav_html += f'<a class="nav-next" href="/brief/articles/"><div class="nav-label">목록으로</div><div class="nav-title">오늘의 정부 발표</div></a>'
        nav_html += '</div>'

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
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<script>
(function(){{ if (/Mobi|Android|iPhone/i.test(navigator.userAgent)) document.documentElement.classList.add('is-mobile'); }})();
</script>
<style>
{ARTICLE_DETAIL_CSS}
</style>
</head>
<body>
<header class="hdr">
  <a class="hdr-logo" href="/">브리핑룸</a>
  <nav class="hdr-nav">
    <a href="/"><span class="lbl-full">홈</span><span class="lbl-short">홈</span></a>
    <a class="on" href="/brief/"><span class="lbl-full">정부 발표</span><span class="lbl-short">정부 발표</span></a>
    <a href="/keywords/"><span class="lbl-full">키워드 트렌드</span><span class="lbl-short">키워드</span></a>
    <a href="/regulation/"><span class="lbl-full">규제 트래커</span><span class="lbl-short">규제</span></a>
  </nav>
</header>
<section class="hero">
  <div class="hero-inner">
    <div class="hero-bc"><a href="/brief/">정부 발표</a><span>/</span><a href="/brief/articles/">오늘의 정부 발표</a><span>/</span>보도자료</div>
    <div class="hero-badges">
      <span class="hero-imp {imp_cls}">영향도 {html.escape(impact)}</span>
      <span class="hero-cat">{html.escape(category)}</span>
      <span class="hero-source">{h_source}</span>
      <span class="hero-date">{date_str}</span>
    </div>
    <h1 class="hero-title">{h_title}</h1>
    <div class="hero-kws">{kw_tags}</div>
  </div>
</section>
<div class="shell">
  {easy_html}
  {points_html}
  {analysis_html}
  {context_html}
  {kw_box_html}
  {attach_html}
  {related_html}
  {_build_reg_links(keywords)}
  {source_html}
  <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);border-radius:10px;padding:20px 24px;margin:16px 0;display:flex;align-items:center;justify-content:space-between;gap:16px">
    <div style="color:#fff"><div style="font-family:var(--serif);font-size:16px;font-weight:700;margin-bottom:4px">매일 정책 브리핑 받기</div><div style="font-size:13px;opacity:.8">정부 발표 요약과 규제 변화를 텔레그램으로 전달합니다</div></div>
    <a href="https://t.me/govbrief" target="_blank" rel="noopener" style="padding:10px 20px;background:#fff;color:#1e40af;border-radius:8px;font-weight:700;font-size:14px;text-decoration:none;white-space:nowrap">구독하기</a>
  </div>
  {nav_html}
</div>
<footer class="footer">
  <div class="footer-motto">정부 정책과 규제 변화, 한 화면에</div>
  <div class="footer-site">govbrief.kr</div>
</footer>
<nav class="bnav">
  <a href="/">홈</a>
  <a class="on" href="/brief/">정부 발표</a>
  <a href="/keywords/">키워드</a>
  <a href="/regulation/">규제</a>
</nav>
</body>
</html>
"""

        article_dir = date_dir / slug
        article_dir.mkdir(parents=True, exist_ok=True)
        (article_dir / "index.html").write_text(article_html, encoding="utf-8")
        count += 1

    print(f"  [Articles] {count}개 기사 HTML 생성 → {date_dir}")
    return count



def generate_today_page(target_date: str, output_path: str = "brief/today", hero_title: str = "오늘의 정부 발표", hero_eyebrow: str = "TODAY'S GOVERNMENT BRIEFING") -> Path:
    """보도자료 목록 페이지 생성 — brief/today/ 또는 brief/date/날짜/"""
    json_path = DATA_DIR / f"{target_date}.json"
    if not json_path.exists():
        print(f"  [Today] {json_path} 없음 → 스킵")
        return None

    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        return None

    date_display = target_date.replace("-", ".")
    from collections import Counter
    from briefingroom.config import CAT_MAP

    # 부처명/인명 제외 키워드 집계
    org_names = set(CAT_MAP.keys())
    person_suffixes = ("총리", "장관", "위원장", "차관", "청장", "처장", "원장", "대통령")
    kw_counter = Counter()
    cat_counter = Counter()
    source_counter = Counter()
    for it in items:
        cat_counter[it.get("category", "기타")] += 1
        source_counter[it.get("source", "")] += 1
        for k in it.get("keywords", []):
            if k in org_names or any(k.endswith(s) for s in person_suffixes):
                continue
            kw_counter[k] += 1

    high_count = sum(1 for it in items if it.get("impact") == "상")
    mid_count = sum(1 for it in items if it.get("impact") == "중")
    dept_count = len(source_counter)

    # 분야 필터 pills
    cat_labels = {"금융경제": "금융경제", "산업기술": "산업기술", "사회복지": "사회복지", "외교안보": "외교안보", "행정법제": "행정법제"}
    cat_pills = f'<span class="fp on" data-f="all">전체 <span class="fc">{len(items)}</span></span>'
    for cat, cnt in cat_counter.most_common():
        label = cat_labels.get(cat, cat)
        cat_pills += f'<span class="fp" data-f="{html.escape(cat)}">{html.escape(label)} <span class="fc">{cnt}</span></span>'

    # 부처 필터 pills
    top_sources = source_counter.most_common(7)
    src_pills = '<span class="fp on" data-s="all">전체</span>'
    for src, cnt in top_sources:
        short = src.replace("부", "").replace("청", "")[:4] if len(src) > 5 else src
        src_pills += f'<span class="fp" data-s="{html.escape(src)}">{html.escape(short)} <span class="fc">{cnt}</span></span>'
    remaining = len(source_counter) - 7
    if remaining > 0:
        src_pills += f'<span class="fp" data-s="more">+{remaining}개</span>'

    # 키워드 필터 pills
    kw_pills = ""
    for kw, cnt in kw_counter.most_common(10):
        kw_pills += f'<a class="fk" href="/brief/articles/?kw={html.escape(kw)}">{html.escape(kw)} <span class="fc">{cnt}</span></a>'

    # 카드 생성
    cards_html = ""
    for it in items:
        slug = it.get("slug", "000")
        imp = it.get("impact", "중")
        imp_cls = "ch" if imp == "상" else ("cm" if imp == "중" else "cl")
        cat = it.get("category", "")
        cat_cls = {"금융경제": "cf", "산업기술": "ci", "사회복지": "cs", "외교안보": "cd", "행정법제": "ca"}.get(cat, "ca")
        cat_label = cat_labels.get(cat, cat)
        source = it.get("source", "")
        title = it.get("title", "")
        easy = it.get("easy_summary", "")
        keywords = it.get("keywords", [])
        date = it.get("date", target_date)

        kw_tags = "".join(f'<span class="ct">{html.escape(k)}</span>' for k in keywords[:4])

        easy_block = ""
        if easy and easy.strip():
            easy_block = f'<div class="ce"><div class="cel">EASY SUMMARY</div>{html.escape(easy.strip())}</div>'

        kw_data = ",".join(keywords[:5]) if keywords else title[:60]
        ai_badge = '<span class="tai">AI 요약</span>' if (easy and easy.strip()) or it.get("summary") else ''
        orig_url = it.get("url", "")
        orig_link = f'<a class="to" href="{html.escape(orig_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">원문</a>' if orig_url else ''

        cards_html += f'''<a class="tc" href="/articles/{date}/{slug}/" data-cat="{html.escape(cat)}" data-src="{html.escape(source)}" data-kw="{html.escape(kw_data)}">
<div class="tt"><span class="ti {imp_cls}">{html.escape(imp)}</span><span class="ts">{html.escape(source)}</span><span class="tg {cat_cls}">{html.escape(cat_label)}</span>{ai_badge}</div>
<div class="tn">{html.escape(title)}</div>
{easy_block}
<div class="ck">{kw_tags}</div>
<div class="tb"><span>{date_display}</span>{orig_link}<span class="tl">상세 보기 &#8594;</span></div>
</a>\n'''

    today_dir = Path(DATA_DIR).parent / output_path
    today_dir.mkdir(parents=True, exist_ok=True)

    today_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{hero_title} - 브리핑룸</title>
<meta name="description" content="{date_display} 정부 보도자료 {len(items)}건을 AI가 분석했습니다.">
<link rel="canonical" href="{SITE_URL}/{output_path}/">
<meta property="og:type" content="website">
<meta property="og:title" content="{hero_title} - 브리핑룸">
<meta property="og:description" content="{date_display} 정부 보도자료 {len(items)}건을 AI가 분석했습니다.">
<meta property="og:url" content="{SITE_URL}/{output_path}/">
<meta property="og:site_name" content="govbrief.kr">
<meta property="og:locale" content="ko_KR">
<meta property="og:image" content="{SITE_URL}/og-image.png">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "{hero_title}",
  "description": "{date_display} 정부 보도자료 {len(items)}건을 AI가 분석했습니다.",
  "url": "{SITE_URL}/{output_path}/",
  "publisher": {{"@type": "Organization", "name": "브리핑룸", "url": "{SITE_URL}"}},
  "numberOfItems": {len(items)}
}}
</script>
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<script>(function(){{if(/Mobi|Android|iPhone/i.test(navigator.userAgent))document.documentElement.classList.add('is-mobile')}})();</script>
<style>
*{{box-sizing:border-box;margin:0;padding:0;word-break:keep-all}}
:root{{--bg:#f7f7f5;--s:#fff;--b:#dcdcd8;--bl:#ededea;--t:#1a1a1a;--t2:#555;--t3:#888;--m:#bbb;--sec:#1e40af;--sec-bg:#eff6ff;--sec-border:#bfdbfe;--red:#dc2626;--red-bg:#fee2e2;--amber:#d97706;--amber-bg:#fef3c7;--green:#047857;--green-bg:#ecfdf5;--purple:#7c3aed;--purple-bg:#f5f3ff;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}}
body{{background:var(--bg);color:var(--t);font-family:var(--sans);font-size:15px;line-height:1.6;min-width:1120px}}
.is-mobile body{{min-width:0;font-size:14px;padding-bottom:68px}}
.hdr{{background:#fff;border-bottom:1px solid var(--b);height:64px;display:flex;align-items:center;padding:0 32px;position:sticky;top:0;z-index:100}}
.hdr-logo{{font-family:var(--serif);font-size:24px;font-weight:700;color:var(--t);text-decoration:none;margin-right:44px}}
.hdr-nav{{display:flex;gap:6px;flex:1}}
.hdr-nav a{{font-size:15px;font-weight:600;color:var(--t2);text-decoration:none;padding:10px 16px;border-radius:6px}}
.hdr-nav a:hover{{background:var(--bl)}}
.hdr-nav a.on{{color:var(--sec);background:var(--sec-bg);font-weight:700}}
.hdr-nav .lbl-short{{display:none}}
.is-mobile .hdr{{height:52px;padding:0 12px}}
.is-mobile .hdr-logo{{font-size:17px;margin-right:8px}}
.is-mobile .hdr-nav a{{font-size:12px;padding:7px 8px}}
.is-mobile .hdr-nav .lbl-full{{display:none}}
.is-mobile .hdr-nav .lbl-short{{display:inline}}
.hero{{background:linear-gradient(180deg,var(--sec-bg),#fff);border-bottom:1px solid var(--sec-border);padding:36px 32px 28px}}
.hero-inner{{max-width:1080px;margin:0 auto}}
.hero-bc{{font-size:12px;color:var(--t3);margin-bottom:12px}}
.hero-bc a{{color:var(--sec);text-decoration:none;font-weight:600}}
.hero-bc span{{margin:0 6px;color:var(--m)}}
.hero-ey{{font-family:var(--mono);font-size:11px;color:var(--sec);font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px}}
.hero-title{{font-family:var(--serif);font-size:30px;font-weight:700;margin-bottom:6px}}
.hero-sub{{font-size:14px;color:var(--t2);line-height:1.7;max-width:640px;margin-bottom:20px}}
.hero-stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;max-width:900px}}
.hs{{background:#fff;border:1px solid var(--sec-border);border-radius:8px;padding:12px 14px}}
.hs .hl{{font-size:10px;color:var(--sec);font-weight:700}}
.hs .hn{{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--sec);line-height:1.1;margin-top:3px}}
.hs .hu{{font-family:var(--sans);font-size:11px;font-weight:600;color:var(--t3)}}
.is-mobile .hero{{padding:20px 16px}}
.is-mobile .hero-title{{font-size:22px}}
.is-mobile .hero-stats{{grid-template-columns:repeat(3,1fr)}}
.shell{{max-width:1080px;margin:0 auto;padding:20px 16px 40px}}
.fb{{background:#fff;border:1px solid var(--b);border-radius:10px;padding:16px 20px;margin-bottom:20px;position:sticky;top:64px;z-index:50}}
.is-mobile .fb{{top:52px;padding:8px 12px;position:sticky}}
.fr{{display:flex;flex-direction:column;align-items:flex-start;gap:10px}}
.fg{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.fl{{font-size:12px;font-weight:700;color:var(--t2);min-width:52px;flex-shrink:0}}
/* 모바일 드롭다운 필터 */
.is-mobile .fr{{display:none}}
.m-filter-tabs{{display:none}}
.is-mobile .m-filter-tabs{{display:flex;gap:6px;align-items:center}}
.m-ftab{{font-size:13px;font-weight:700;color:var(--t2);padding:6px 12px;border-radius:6px;border:1px solid var(--b);background:#fff;cursor:pointer;flex:1;text-align:center}}
.m-ftab.active{{color:var(--sec);border-color:var(--sec);background:var(--sec-bg)}}
.m-ftab .m-sel{{font-size:10px;color:var(--sec);display:block;font-weight:600;margin-top:1px}}
.m-fdrop{{display:none;padding:8px 0}}
.m-fdrop.show{{display:flex;flex-wrap:wrap;gap:5px}}
.m-fdrop .fp,.m-fdrop .fk{{font-size:11px;padding:4px 10px}}
.fps{{display:flex;flex-wrap:wrap;gap:6px}}
.fp{{font-size:12px;font-weight:600;padding:5px 12px;border-radius:6px;border:1px solid var(--b);background:#fff;color:var(--t2);cursor:pointer}}
.fp:hover{{border-color:var(--sec);color:var(--sec)}}
.fp.on{{background:var(--sec);color:#fff;border-color:var(--sec)}}
.fc{{font-family:var(--mono);font-size:10px;margin-left:3px;opacity:.7}}
.fk{{font-size:12px;font-weight:600;padding:5px 12px;border-radius:6px;border:1px solid var(--sec-border);background:#fff;color:var(--sec);text-decoration:none;cursor:pointer}}
.fk:hover{{background:var(--sec);color:#fff;border-color:var(--sec)}}
.fk.on{{background:var(--sec);color:#fff;border-color:var(--sec)}}
.frs{{font-size:11px;color:var(--t3);cursor:pointer;font-weight:600;text-decoration:underline;flex-shrink:0}}
.lt{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding:0 4px}}
.ls{{display:flex;gap:4px}}
.lsb{{font-size:12px;font-weight:600;color:var(--t3);padding:4px 10px;border-radius:4px;cursor:pointer;border:1px solid transparent}}
.lsb.on{{color:var(--sec);border-color:var(--sec-border);background:var(--sec-bg)}}
.lc{{font-size:13px;color:var(--t2)}}
.lc strong{{font-family:var(--mono);color:var(--sec)}}
.tc{{background:#fff;border:1px solid var(--b);border-radius:10px;padding:20px 22px;margin-bottom:10px;text-decoration:none;color:var(--t);display:block;border-left:3px solid var(--b)}}
.tc:hover{{box-shadow:0 2px 8px rgba(0,0,0,.04)}}
.tc[data-imp="상"]{{border-left-color:var(--red)}}
.tt{{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}}
.ti{{font-family:var(--mono);font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px}}
.ch{{background:var(--red-bg);color:var(--red)}}
.cm{{background:var(--amber-bg);color:var(--amber)}}
.cl{{background:#f3f4f6;color:#6b7280}}
.ts{{font-size:12px;color:var(--t3);font-weight:600}}
.tg{{font-size:11px;font-weight:600;padding:2px 8px;border-radius:4px;margin-left:auto}}
.cf{{color:var(--sec);background:var(--sec-bg)}}
.ci{{color:var(--green);background:var(--green-bg)}}
.cs{{color:var(--purple);background:var(--purple-bg)}}
.cd{{color:var(--amber);background:var(--amber-bg)}}
.ca{{color:var(--t3);background:#f3f4f6}}
.tn{{font-family:var(--serif);font-size:17px;font-weight:700;line-height:1.4;margin-bottom:10px}}
.ce{{font-size:14px;color:var(--t2);line-height:1.8;background:var(--sec-bg);border-left:3px solid var(--sec);border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:10px}}
.cel{{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--sec);letter-spacing:.06em;margin-bottom:4px}}
.ck{{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px}}
.ct{{font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;border:1px solid var(--bl);color:var(--t3)}}
.tai{{font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;background:#dbeafe;color:#1e40af;margin-left:4px}}
.to{{font-size:11px;color:var(--t3);text-decoration:none;font-weight:600;padding:2px 8px;border:1px solid var(--bl);border-radius:4px;margin-left:auto}}
.to:hover{{color:var(--sec);border-color:var(--sec-border)}}
.tb{{display:flex;align-items:center;justify-content:space-between;font-size:11px;color:var(--t3);gap:8px}}
.tl{{color:var(--sec);font-weight:600}}
.impact-legend{{background:var(--s);border:1px solid var(--bl);border-radius:8px;padding:14px 18px;margin:16px 0 0;font-size:13px;color:var(--t2);line-height:1.7}}
.impact-legend-title{{font-size:12px;font-weight:700;color:var(--t3);margin-bottom:6px}}
.impact-legend-row{{display:flex;align-items:center;gap:8px;margin-bottom:2px}}
.impact-legend-row:last-child{{margin-bottom:0}}
.footer{{max-width:1080px;margin:20px auto 0;padding:24px 16px;text-align:center;color:var(--t3);border-top:1px solid var(--bl)}}
.footer-motto{{font-family:var(--serif);font-size:14px;color:var(--t2)}}
.footer-site{{font-family:var(--mono);font-size:11px;color:var(--t3);margin-top:4px}}
.bnav{{display:none}}
.is-mobile .bnav{{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;bottom:0;left:0;right:0;z-index:200;background:#fff;border-top:1px solid var(--b);padding:8px 0 calc(10px + env(safe-area-inset-bottom))}}
.bnav a{{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--t3);font-size:10.5px;font-weight:600}}
.bnav a.on{{color:var(--sec)}}
.pag{{display:flex;justify-content:center;align-items:center;gap:4px;margin-top:24px;padding:16px 0}}
.pb{{font-family:var(--mono);font-size:13px;font-weight:600;padding:8px 14px;border-radius:6px;border:1px solid var(--b);background:#fff;color:var(--t2);cursor:pointer}}
.pb:hover{{border-color:var(--sec);color:var(--sec)}}
.pb.on{{background:var(--sec);color:#fff;border-color:var(--sec)}}
.pb.off{{opacity:.3;pointer-events:none}}
</style>
</head>
<body>
<header class="hdr">
  <a class="hdr-logo" href="/">브리핑룸</a>
  <nav class="hdr-nav">
    <a href="/"><span class="lbl-full">홈</span><span class="lbl-short">홈</span></a>
    <a class="on" href="/brief/"><span class="lbl-full">정부 발표</span><span class="lbl-short">정부 발표</span></a>
    <a href="/keywords/"><span class="lbl-full">키워드 트렌드</span><span class="lbl-short">키워드</span></a>
    <a href="/regulation/"><span class="lbl-full">규제 트래커</span><span class="lbl-short">규제</span></a>
  </nav>
</header>
<section class="hero">
  <div class="hero-inner">
    <div class="hero-bc"><a href="/brief/">정부 발표</a><span>/</span>오늘의 정부 발표</div>
    <div class="hero-ey">{hero_eyebrow}</div>
    <h1 class="hero-title">{hero_title}</h1>
    <p class="hero-sub">{date_display} 51개 부처에서 발표한 보도자료를 AI가 분석했습니다.</p>
    <div class="hero-stats">
      <div class="hs"><div class="hl">전체 발표</div><div class="hn">{len(items)}<span class="hu">건</span></div></div>
      <div class="hs"><div class="hl">참여 부처</div><div class="hn">{dept_count}<span class="hu">개</span></div></div>
      <div class="hs"><div class="hl">영향도 상</div><div class="hn">{high_count}<span class="hu">건</span></div></div>
      <div class="hs"><div class="hl">영향도 중</div><div class="hn">{mid_count}<span class="hu">건</span></div></div>
      <div class="hs"><div class="hl">영향도 하</div><div class="hn">{len(items) - high_count - mid_count}<span class="hu">건</span></div></div>
    </div>
  </div>
</section>
<div class="shell">
  <div class="fb">
    <!-- 데스크톱 필터 -->
    <div class="fr">
      <div class="fg"><span class="fl">분야</span><div class="fps" id="f-cat">{cat_pills}</div></div>
      <div class="fg"><span class="fl">부처</span><div class="fps" id="f-src">{src_pills}</div></div>
      <div class="fg"><span class="fl">키워드</span><div class="fps">{kw_pills}</div><span class="frs" id="f-reset">초기화</span></div>
    </div>
    <!-- 모바일 드롭다운 필터 -->
    <div class="m-filter-tabs">
      <div class="m-ftab" data-target="m-drop-cat">분야<span class="m-sel" id="m-cat-sel">전체</span></div>
      <div class="m-ftab" data-target="m-drop-src">부처<span class="m-sel" id="m-src-sel">전체</span></div>
      <div class="m-ftab" data-target="m-drop-kw">키워드<span class="m-sel" id="m-kw-sel">전체</span></div>
      <div class="m-ftab" id="m-reset" style="flex:0;padding:6px 10px;font-size:11px;color:var(--t3)">초기화</div>
    </div>
    <div class="m-fdrop" id="m-drop-cat"><div class="fps" id="mf-cat">{cat_pills}</div></div>
    <div class="m-fdrop" id="m-drop-src"><div class="fps" id="mf-src">{src_pills}</div></div>
    <div class="m-fdrop" id="m-drop-kw"><div class="fps">{kw_pills}</div></div>
  </div>
  <div class="lt">
    <div class="ls"><span class="lsb on" id="sort-imp">영향도순</span><span class="lsb" id="sort-new">최신순</span></div>
    <div class="lc">총 <strong id="vis-count">{len(items)}</strong>건 표시 중</div>
  </div>
  <div id="card-list">
{cards_html}
  </div>
  <div class="pag" id="pag"></div>
  <div class="impact-legend">
    <div class="impact-legend-title">영향도 기준</div>
    <div class="impact-legend-row"><span class="ti ch">상</span> 국민 생활·경제에 직접 영향. 법령 제·개정, 예산 편성, 규제 변경 등</div>
    <div class="impact-legend-row"><span class="ti cm">중</span> 특정 업계·부처 관련 정책 발표. 간접적 영향 가능성</div>
    <div class="impact-legend-row"><span class="ti cl">하</span> 내부 인사, 행사 안내, 참고자료 등 정보성 발표</div>
  </div>
</div>
<footer class="footer">
  <div class="footer-motto">정부 정책과 규제 변화, 한 화면에</div>
  <div class="footer-site">govbrief.kr</div>
</footer>
<nav class="bnav">
  <a href="/">홈</a><a class="on" href="/brief/">정부 발표</a><a href="/keywords/">키워드</a><a href="/regulation/">규제</a>
</nav>
<script>
(function(){{
  var PER=10, page=1, activeCat='all', activeSrc='all', activeKw='';
  var allCards=[].slice.call(document.querySelectorAll('.tc'));

  // URL ?kw= 파라미터 읽기
  var urlKw=new URLSearchParams(window.location.search).get('kw')||'';
  if(urlKw)activeKw=urlKw;

  function getFiltered(){{
    return allCards.filter(function(c){{
      var catOk=activeCat==='all'||c.dataset.cat===activeCat;
      var srcOk=activeSrc==='all'||c.dataset.src===activeSrc;
      var kwOk=!activeKw||(c.dataset.kw&&c.dataset.kw.indexOf(activeKw)!==-1);
      return catOk&&srcOk&&kwOk;
    }});
  }}

  function render(){{
    var filtered=getFiltered();
    var total=filtered.length;
    var pages=Math.ceil(total/PER)||1;
    if(page>pages)page=pages;
    var start=(page-1)*PER, end=start+PER;

    allCards.forEach(function(c){{c.style.display='none'}});
    filtered.forEach(function(c,i){{
      c.style.display=(i>=start&&i<end)?'':'none';
    }});

    document.getElementById('vis-count').textContent=total;

    // 페이지네이션 렌더
    var pagEl=document.getElementById('pag');
    var h='<span class="pb'+(page<=1?' off':'')+'" data-p="prev">&#8592; 이전</span>';
    for(var i=1;i<=pages;i++){{
      if(pages>7&&i>3&&i<pages-1&&Math.abs(i-page)>1){{
        if(i===4||i===pages-2)h+='<span style="padding:0 4px;color:var(--t3)">...</span>';
        continue;
      }}
      h+='<span class="pb'+(i===page?' on':'')+'" data-p="'+i+'">'+i+'</span>';
    }}
    h+='<span class="pb'+(page>=pages?' off':'')+'" data-p="next">다음 &#8594;</span>';
    pagEl.innerHTML=h;
  }}

  document.getElementById('pag').addEventListener('click',function(e){{
    var t=e.target.closest('.pb');if(!t||t.classList.contains('off'))return;
    var v=t.dataset.p;
    var filtered=getFiltered();
    var pages=Math.ceil(filtered.length/PER)||1;
    if(v==='prev')page=Math.max(1,page-1);
    else if(v==='next')page=Math.min(pages,page+1);
    else page=parseInt(v)||1;
    render();
    window.scrollTo({{top:document.getElementById('card-list').offsetTop-80,behavior:'smooth'}});
  }});

  document.getElementById('f-cat').addEventListener('click',function(e){{
    var t=e.target.closest('.fp');if(!t)return;
    this.querySelectorAll('.fp').forEach(function(p){{p.classList.remove('on')}});
    t.classList.add('on');
    activeCat=t.dataset.f||'all';
    page=1;render();
  }});
  document.getElementById('f-src').addEventListener('click',function(e){{
    var t=e.target.closest('.fp');if(!t)return;
    this.querySelectorAll('.fp').forEach(function(p){{p.classList.remove('on')}});
    t.classList.add('on');
    activeSrc=t.dataset.s||'all';
    page=1;render();
  }});
  document.getElementById('f-reset').addEventListener('click',function(){{
    activeCat='all';activeSrc='all';activeKw='';page=1;
    document.querySelectorAll('.fp').forEach(function(p){{p.classList.remove('on')}});
    document.querySelector('#f-cat .fp').classList.add('on');
    document.querySelector('#f-src .fp').classList.add('on');
    document.querySelectorAll('.fk').forEach(function(k){{k.classList.remove('on')}});
    history.replaceState(null,'',location.pathname);
    render();
  }});

  // 키워드 pill 클릭 시 필터링 (페이지 이동 대신 인라인 필터)
  document.querySelectorAll('.fk').forEach(function(k){{
    k.addEventListener('click',function(e){{
      e.preventDefault();
      var kw=this.textContent.trim().replace(/\\s*\\d+$/,'');
      if(activeKw===kw){{activeKw='';this.classList.remove('on')}}
      else{{activeKw=kw;document.querySelectorAll('.fk').forEach(function(f){{f.classList.remove('on')}});this.classList.add('on')}}
      page=1;render();
    }});
  }});

  // URL kw 파라미터가 있으면 해당 키워드 pill 활성화
  if(activeKw){{
    document.querySelectorAll('.fk').forEach(function(k){{
      if(k.textContent.trim().replace(/\\s*\\d+$/,'')===activeKw)k.classList.add('on');
    }});
  }}

  // 모바일 드롭다운 토글
  document.querySelectorAll('.m-ftab[data-target]').forEach(function(tab){{
    tab.addEventListener('click',function(){{
      var target=document.getElementById(this.dataset.target);
      var isOpen=target.classList.contains('show');
      document.querySelectorAll('.m-fdrop').forEach(function(d){{d.classList.remove('show')}});
      document.querySelectorAll('.m-ftab[data-target]').forEach(function(t){{t.classList.remove('active')}});
      if(!isOpen){{target.classList.add('show');this.classList.add('active')}}
    }});
  }});

  // 모바일 분야 필터
  document.getElementById('mf-cat').addEventListener('click',function(e){{
    var t=e.target.closest('.fp');if(!t)return;
    this.querySelectorAll('.fp').forEach(function(p){{p.classList.remove('on')}});
    t.classList.add('on');
    activeCat=t.dataset.f||'all';
    page=1;
    var label=activeCat==='all'?'전체':t.textContent.replace(/\\d+/g,'').trim();
    document.getElementById('m-cat-sel').textContent=label;
    // 데스크톱도 동기화
    document.querySelectorAll('#f-cat .fp').forEach(function(p){{p.classList.remove('on');if((p.dataset.f||'all')===activeCat)p.classList.add('on')}});
    document.querySelectorAll('.m-fdrop').forEach(function(d){{d.classList.remove('show')}});
    document.querySelectorAll('.m-ftab[data-target]').forEach(function(t2){{t2.classList.remove('active')}});
    render();
  }});

  // 모바일 부처 필터
  document.getElementById('mf-src').addEventListener('click',function(e){{
    var t=e.target.closest('.fp');if(!t)return;
    this.querySelectorAll('.fp').forEach(function(p){{p.classList.remove('on')}});
    t.classList.add('on');
    activeSrc=t.dataset.s||'all';
    page=1;
    var label=activeSrc==='all'?'전체':t.textContent.replace(/\\d+/g,'').trim();
    document.getElementById('m-src-sel').textContent=label;
    document.querySelectorAll('#f-src .fp').forEach(function(p){{p.classList.remove('on');if((p.dataset.s||'all')===activeSrc)p.classList.add('on')}});
    document.querySelectorAll('.m-fdrop').forEach(function(d){{d.classList.remove('show')}});
    document.querySelectorAll('.m-ftab[data-target]').forEach(function(t2){{t2.classList.remove('active')}});
    render();
  }});

  // 모바일 키워드 필터
  document.querySelectorAll('#m-drop-kw .fk').forEach(function(k){{
    k.addEventListener('click',function(e){{
      e.preventDefault();
      var kw=this.textContent.trim().replace(/\\s*\\d+$/,'');
      if(activeKw===kw){{activeKw='';this.classList.remove('on');document.getElementById('m-kw-sel').textContent='전체'}}
      else{{activeKw=kw;document.querySelectorAll('#m-drop-kw .fk').forEach(function(f){{f.classList.remove('on')}});this.classList.add('on');document.getElementById('m-kw-sel').textContent=kw}}
      // 데스크톱도 동기화
      document.querySelectorAll('.fr .fk').forEach(function(f){{f.classList.remove('on');if(f.textContent.trim().replace(/\\s*\\d+$/,'')===activeKw)f.classList.add('on')}});
      page=1;
      document.querySelectorAll('.m-fdrop').forEach(function(d){{d.classList.remove('show')}});
      document.querySelectorAll('.m-ftab[data-target]').forEach(function(t2){{t2.classList.remove('active')}});
      render();
    }});
  }});

  // 모바일 초기화
  document.getElementById('m-reset').addEventListener('click',function(){{
    activeCat='all';activeSrc='all';activeKw='';page=1;
    document.querySelectorAll('.fp').forEach(function(p){{p.classList.remove('on')}});
    document.querySelectorAll('#f-cat .fp:first-child,#f-src .fp:first-child,#mf-cat .fp:first-child,#mf-src .fp:first-child').forEach(function(p){{p.classList.add('on')}});
    document.querySelectorAll('.fk').forEach(function(k){{k.classList.remove('on')}});
    document.getElementById('m-cat-sel').textContent='전체';
    document.getElementById('m-src-sel').textContent='전체';
    document.getElementById('m-kw-sel').textContent='전체';
    document.querySelectorAll('.m-fdrop').forEach(function(d){{d.classList.remove('show')}});
    document.querySelectorAll('.m-ftab[data-target]').forEach(function(t2){{t2.classList.remove('active')}});
    history.replaceState(null,'',location.pathname);
    render();
  }});

  // URL kw가 있으면 모바일 키워드 라벨도 업데이트
  if(activeKw){{
    document.getElementById('m-kw-sel').textContent=activeKw;
  }}

  render();
}})();
</script>
</body>
</html>"""

    out_path = today_dir / "index.html"
    out_path.write_text(today_html, encoding="utf-8")
    print(f"  [DatePage] {output_path}/index.html 생성 ({len(items)}건, {date_display})")
    return out_path


def generate_date_pages() -> int:
    """모든 일자별 보도자료 페이지 생성 (/brief/date/2026-04-10/ 등)"""
    import glob as _glob
    json_files = sorted(_glob.glob(str(DATA_DIR / "2026-*.json")))
    count = 0
    for jf in json_files:
        date_str = Path(jf).stem
        date_display = date_str.replace("-", ". ")
        generate_today_page(
            target_date=date_str,
            output_path=f"brief/date/{date_str}",
            hero_title=f"{date_display} 정부 발표",
            hero_eyebrow="DAILY GOVERNMENT BRIEFING",
        )
        count += 1
    print(f"  [DatePages] {count}일치 일자별 페이지 생성 완료")
    return count


def generate_sitemap(target_date: str) -> Path:
    """sitemap.xml 생성 — 날짜별 아카이브 + 기사 페이지 URL"""
    import glob as _glob

    urls = [
        # 메인
        f'  <url><loc>{SITE_URL}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
        # 정부 발표
        f'  <url><loc>{SITE_URL}/brief/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>{SITE_URL}/brief/today/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>{SITE_URL}/brief/weekly/</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{SITE_URL}/brief/ai/</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>',
        # 키워드
        f'  <url><loc>{SITE_URL}/keywords/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>{SITE_URL}/keywords/press/</loc><changefreq>daily</changefreq><priority>0.7</priority></url>',
        # 규제
        f'  <url><loc>{SITE_URL}/regulation/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>{SITE_URL}/regulation/finlaw/</loc><changefreq>daily</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{SITE_URL}/regulation/finlaw/cases/</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>',
        f'  <url><loc>{SITE_URL}/regulation/finlaw/opinions/</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>',
        f'  <url><loc>{SITE_URL}/regulation/finlaw/issues/</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>',
        f'  <url><loc>{SITE_URL}/regulation/realestate/</loc><changefreq>daily</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{SITE_URL}/regulation/realestate/cases/</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>',
        f'  <url><loc>{SITE_URL}/regulation/cross/</loc><changefreq>daily</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{SITE_URL}/regulation/finlaw-gpt/</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>',
    ]

    base = Path(DATA_DIR).parent

    # 일자별 보도자료 페이지 (/brief/date/2026-04-14/)
    date_dir = base / "brief" / "date"
    if date_dir.exists():
        for d in sorted(date_dir.iterdir()):
            if d.is_dir() and (d / "index.html").exists():
                urls.append(f'  <url><loc>{SITE_URL}/brief/date/{d.name}/</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>')

    # 주간 보고서 (/brief/weekly/2026-04-12/)
    weekly_dir = base / "brief" / "weekly"
    if weekly_dir.exists():
        for d in sorted(weekly_dir.iterdir()):
            if d.is_dir() and (d / "index.html").exists():
                urls.append(f'  <url><loc>{SITE_URL}/brief/weekly/{d.name}/</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>')

    # 법령 상세 페이지 (regulation/finlaw/detail/)
    detail_dir = base / "regulation" / "finlaw" / "detail"
    if detail_dir.exists():
        for d in sorted(detail_dir.iterdir()):
            if d.is_dir() and (d / "index.html").exists():
                urls.append(f'  <url><loc>{SITE_URL}/regulation/finlaw/detail/{d.name}/</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>')

    # 판례 상세 페이지 (regulation/finlaw/cases/)
    cases_dir = base / "regulation" / "finlaw" / "cases"
    if cases_dir.exists():
        for d in sorted(cases_dir.iterdir()):
            if d.is_dir() and (d / "index.html").exists():
                urls.append(f'  <url><loc>{SITE_URL}/regulation/finlaw/cases/{d.name}/</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>')

    # 법령 diff 페이지 (regulation/finlaw/diff/)
    diff_dir = base / "regulation" / "finlaw" / "diff"
    if diff_dir.exists():
        for d in sorted(diff_dir.iterdir()):
            if d.is_dir() and (d / "index.html").exists():
                urls.append(f'  <url><loc>{SITE_URL}/regulation/finlaw/diff/{d.name}/</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>')

    # 날짜별 JSON에서 기사 URL 수집
    for json_file in sorted(Path(DATA_DIR).glob("20*.json")):
        date_str = json_file.stem
        if "weekly" in date_str or "schedule" in date_str or "latest" in date_str:
            continue
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
    """정적 사이트 전체 생성"""
    print(f"\n{'─' * 60}")
    print("[정적 사이트 생성 중...]")
    generate_home(target_date)
    generate_policy_page(target_date)
    generate_finlaw_index()
    generate_cases_page()
    generate_notices_page()
    generate_rss(target_date)
    generate_article_pages(target_date)
    generate_today_page(target_date)
    generate_date_pages()
    generate_sitemap(target_date)
