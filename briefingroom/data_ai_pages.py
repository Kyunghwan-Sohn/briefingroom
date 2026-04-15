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

from briefingroom.config import BASE_DIR

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
    <a class="on" href="/regulation/">금융/부동산 규제</a>
  </nav>
</header>"""

FOOTER_HTML = """<footer style="max-width:1080px;margin:20px auto 0;padding:24px 16px;text-align:center;color:var(--t3);border-top:1px solid var(--bl)">
  <div style="font-family:var(--serif);font-size:14px;color:var(--t2)">정부 정책과 금융/부동산 규제, 한 화면에</div>
  <div style="font-family:var(--mono);font-size:11px;color:var(--t3);margin-top:4px">govbrief.kr</div>
</footer>
<nav class="bnav"><a href="/">홈</a><a href="/brief/">정부 발표</a><a href="/keywords/">키워드</a><a class="on" href="/regulation/">금융/부동산</a></nav>"""


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


def generate_law_detail_page(law: dict) -> Path:
    """개별 법령 상세 페이지 생성"""
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
  <div class="sec-hdr">조문 전문 ({len(articles)}개)</div>
  {articles_html}
</div>
{FOOTER_HTML}
</body>
</html>"""

    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return out_dir


def generate_timeline_page(laws: list[dict]) -> Path:
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
<div style="display:flex;align-items:center;gap:12px;margin-top:8px">
  <span style="font-family:var(--mono);font-size:12px;color:var(--sec);font-weight:700">조문 {entry['article_count']}개</span>
  <a href="/regulation/data-ai/laws/{entry['law_id']}/" style="font-size:13px;color:var(--sec);font-weight:600;text-decoration:none">조문 전문 보기 &#8594;</a>
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

    # 1. 법령 상세 페이지
    for law in laws:
        if law["article_count"] > 0:
            generate_law_detail_page(law)
            print(f"  [Law] {law['name']}: 조문 {law['article_count']}개")

    # 2. 타임라인 페이지 (본법만, 시행령 제외)
    main_laws = [l for l in laws if "시행령" not in l["name"] and "시행규칙" not in l["name"]]
    generate_timeline_page(main_laws)

    print(f"[data-ai-pages] 완료: 법령 상세 {sum(1 for l in laws if l['article_count'] > 0)}개 + 타임라인 1개")


if __name__ == "__main__":
    main()
