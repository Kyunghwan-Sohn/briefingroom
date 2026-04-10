"""주간 정책 브리핑 — 분석 + PDF + HTML 포스트 + 텔레그램 요약

McKinsey/BCG 스타일 애널리스트 리포트 자동 생성.
매주 일요일 10:00 KST 실행.
"""
from __future__ import annotations

import html as _html
import os
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from briefingroom.config import BASE_DIR, CAT_MAP, DATA_DIR
from briefingroom.llm import generate_weekly_signals
from briefingroom.site_templates import SITE_BASE_CSS, SITE_FONT_LINKS, SITE_NAV_CSS, render_crosslinks, render_top_nav
from briefingroom.weekly_analysis import analyze_weekly, select_weekly_top
from briefingroom.telegram import (
    CAT_ORDER, SITE_URL, _escape_html, send_telegram,
    TELEGRAM_ENABLED,
)

ARTICLES_DIR = BASE_DIR / "articles"

# ═══════════════════════════════════════════════════════════
#  2. 텍스트 유틸
# ═══════════════════════════════════════════════════════════

CAT_NAMES = {
    "금융경제": "금융·경제", "사회복지": "사회·복지",
    "산업기술": "산업·기술", "외교안보": "외교·안보",
    "행정법제": "행정·법제",
}

def _safe(text: str) -> str:
    """PDF용 — HTML 엔티티 디코딩 + 폰트 미지원 문자 치환"""
    text = _html.unescape(str(text))
    half = len(text) // 2
    if half > 15 and text[:half].strip() == text[half:half * 2].strip():
        text = text[:half].strip()
    rep = {
        '\u2018': "'", '\u2019': "'", '\u201C': '"', '\u201D': '"',
        '\uFF62': '[', '\uFF63': ']', '\u300C': '[', '\u300D': ']',
        '\xa0': ' ', '\u33A1': 'm2', '\u00B7': ',', '\u2027': '.',
        '\u2026': '...', '\u2013': '-', '\u2014': '-', '\u200B': '',
    }
    for o, n in rep.items():
        text = text.replace(o, n)
    out = []
    for ch in text:
        cp = ord(ch)
        if cp < 128 or (0xAC00 <= cp <= 0xD7A3) or (0x3131 <= cp <= 0x318E):
            out.append(ch)
    return ''.join(out)


def _clean(text: str) -> str:
    """HTML 엔티티 디코딩 + 제목 중복 제거"""
    text = _html.unescape(str(text))
    half = len(text) // 2
    if half > 15 and text[:half].strip() == text[half:half * 2].strip():
        text = text[:half].strip()
    return text


def _cut(text: str, max_len: int = 250) -> str:
    """문장 단위 자르기"""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    for end in ["다.", "다.'", "다.\"", "다)"]:
        idx = cut.rfind(end)
        if idx > max_len * 0.4:
            return cut[:idx + len(end)]
    idx = cut.rfind(".")
    if idx > max_len * 0.4:
        return cut[:idx + 1]
    return cut + "..."


def _get_summary(item: dict) -> str:
    """아이템에서 정제된 요약 추출"""
    s = _clean(item.get("summary", ""))
    if s.startswith("요약:"):
        s = s.replace("요약:", "").strip()
    return _cut(s.split("키워드:")[0].strip())


def _article_link(item: dict, extra: dict | None = None) -> str:
    d = item.get("date", "")
    slug = item.get("slug", "000") or "000"
    url = f"{SITE_URL}/articles/{d}/{slug}/" if d else SITE_URL
    if not extra:
        return url
    from briefingroom.telegram import _append_query
    return _append_query(url, **extra)


def _find_item_by_title(analysis: dict, title: str) -> dict | None:
    target = (title or "").strip()
    if not target:
        return None
    for items in analysis["items_by_cat"].values():
        for item in items:
            if item.get("title", "").strip() == target:
                return item
    return None


def _fallback_weekly_signals(analysis: dict, selected: dict) -> list[dict]:
    top_kw = [kw for kw, _ in analysis["keywords"].most_common(8)]
    source_rank = analysis["by_source"].most_common(3)
    selected_items = [row[1] for row in selected.values() if row and row[1]]
    signals: list[dict] = []

    if top_kw:
        anchor = selected_items[0] if selected_items else {}
        signals.append({
            "title": f"{top_kw[0]} 정책 확산",
            "evidence": f"'{top_kw[0]}' 키워드 {analysis['keywords'].get(top_kw[0], 0)}회 등장, 전체 {analysis['sources_count']}개 부처 흐름과 연결",
            "related_title": anchor.get("title", ""),
        })

    for cat, _ in CAT_ORDER:
        if cat not in selected:
            continue
        src, item, count, news_cnt, _ = selected[cat]
        signals.append({
            "title": f"{CAT_NAMES.get(cat, cat)} 이슈 부상",
            "evidence": f"{CAT_NAMES.get(cat, cat)} 보도자료 {analysis['by_cat'].get(cat, 0)}건, {src} 발표안 뉴스 인용 {news_cnt}건",
            "related_title": item.get("title", ""),
        })
        if len(signals) >= 5:
            break

    if len(signals) < 5 and source_rank:
        for source, count in source_rank:
            related = next((it for it in selected_items if it.get("source") == source), selected_items[0] if selected_items else {})
            signals.append({
                "title": f"{source} 발표 집중",
                "evidence": f"{source} 주간 보도자료 {count}건으로 상위권, 전주 대비 정책 노출 증가 흐름",
                "related_title": related.get("title", ""),
            })
            if len(signals) >= 5:
                break

    return signals[:5]


def build_weekly_signals(analysis: dict, selected: dict) -> list[dict]:
    selected_payload = []
    for cat, (src, item, count, news_cnt, articles) in selected.items():
        selected_payload.append({
            "category": cat,
            "source": src,
            "title": item.get("title", ""),
            "date": item.get("date", ""),
            "slug": item.get("slug", ""),
            "news_count": news_cnt,
            "summary": _get_summary(item),
        })

    payload = {
        "period": {
            "start": analysis["start"].isoformat(),
            "end": analysis["end"].isoformat(),
        },
        "totals": {
            "articles": analysis["total"],
            "sources": analysis["sources_count"],
            "prev_articles": analysis["prev_total"],
        },
        "by_category": analysis["by_cat"],
        "top_keywords": [{"keyword": kw, "count": count} for kw, count in analysis["keywords"].most_common(10)],
        "keyword_delta": analysis["kw_delta"],
        "selected_articles": selected_payload,
    }

    signals = generate_weekly_signals(payload) or _fallback_weekly_signals(analysis, selected)
    enriched = []
    seen_titles = set()
    for signal in signals:
        related_title = signal.get("related_title", "")
        related_item = _find_item_by_title(analysis, related_title)
        if related_title in seen_titles and related_item is None:
            continue
        seen_titles.add(related_title)
        enriched.append({
            "title": signal.get("title", "").strip(),
            "evidence": signal.get("evidence", "").strip(),
            "related_title": related_title,
            "related_item": related_item,
        })
    return enriched[:5]


# ═══════════════════════════════════════════════════════════
#  3. PDF 생성
# ═══════════════════════════════════════════════════════════

def _ensure_fonts() -> tuple[str, str]:
    """NanumGothic 폰트 확보"""
    font_dir = "/tmp/fonts"
    os.makedirs(font_dir, exist_ok=True)
    reg = f"{font_dir}/NanumGothic-Regular.ttf"
    bold = f"{font_dir}/NanumGothic-Bold.ttf"
    if not os.path.exists(reg):
        import urllib.request
        urllib.request.urlretrieve(
            "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf", reg)
        urllib.request.urlretrieve(
            "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf", bold)
    return reg, bold


def generate_pdf(analysis: dict, selected: dict, target: date) -> Path:
    """시그널 중심 주간 리포트 PDF 생성"""
    from fpdf import FPDF

    reg, bold = _ensure_fonts()
    s = analysis["start"]
    e = analysis["end"]
    top_kw = [kw for kw, _ in analysis["keywords"].most_common(5)]
    signals = build_weekly_signals(analysis, selected)
    colors = [(47, 84, 235), (196, 145, 53), (15, 107, 58), (154, 74, 10), (163, 21, 21)]

    class R(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("NG", "", 7)
            self.set_text_color(160, 160, 160)
            self.cell(0, 10, f"govbrief.kr  |  p.{self.page_no()}", align="C")

    pdf = R()
    pdf.add_font("NG", "", reg)
    pdf.add_font("NG", "B", bold)
    pdf.set_auto_page_break(auto=True, margin=18)
    W = lambda: pdf.w - pdf.l_margin - pdf.r_margin

    def sec(num, title):
        pdf.set_font("NG", "B", 7); pdf.set_text_color(42, 60, 100)
        pdf.cell(0, 4, f"SECTION {num}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("NG", "B", 16); pdf.set_text_color(20, 20, 40)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(42, 60, 100); pdf.set_line_width(0.5)
        pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.l_margin + 40, pdf.get_y() + 1)
        pdf.ln(6)

    def body(text, sz=9, b=False):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("NG", "B" if b else "", sz)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(W(), sz * 0.6, _safe(text))

    # -- COVER --
    pdf.add_page(); pdf.ln(50)
    pdf.set_font("NG", "", 10); pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "WEEKLY POLICY INTELLIGENCE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("NG", "B", 28); pdf.set_text_color(20, 20, 40)
    pdf.cell(0, 14, "주간 정책 브리핑", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("NG", "", 12); pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, f"{s.year}년 {s.month}월 {s.day}일 - {e.month}월 {e.day}일", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_draw_color(42, 60, 100); pdf.set_line_width(0.8)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(15)
    pdf.set_font("NG", "", 9); pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"govbrief.kr  |  {date.today()}", align="C", new_x="LMARGIN", new_y="NEXT")

    # -- SIGNAL DASHBOARD --
    pdf.add_page(); sec("01", "이번 주 정책 시그널 5개")
    td = analysis["total"] - analysis["prev_total"]
    y0 = pdf.get_y()
    for i, (l, v) in enumerate([("총 보도자료", f"{analysis['total']}건"),
                                 ("참여 부처", f"{analysis['sources_count']}개"),
                                 ("전주 대비", f"{td:+d}건")]):
        x = pdf.l_margin + i * 45
        pdf.set_xy(x, y0); pdf.set_font("NG", "", 7); pdf.set_text_color(120, 120, 120)
        pdf.cell(45, 4, l)
        pdf.set_xy(x, y0 + 4); pdf.set_font("NG", "B", 14); pdf.set_text_color(42, 60, 100)
        pdf.cell(45, 8, v)
    pdf.set_y(y0 + 18); pdf.ln(3)
    body(f"핵심 키워드:  {'  |  '.join(f'#{kw}' for kw in top_kw)}", sz=9, b=True)
    pdf.ln(4)

    for idx, signal in enumerate(signals, start=1):
        if pdf.get_y() > 235:
            pdf.add_page()
        item = signal.get("related_item") or {}
        pdf.set_draw_color(*colors[(idx - 1) % len(colors)])
        pdf.set_line_width(1.8)
        x = pdf.l_margin
        y = pdf.get_y()
        pdf.line(x, y, x, y + 22)
        pdf.set_xy(x + 5, y)
        pdf.set_font("NG", "B", 12)
        pdf.set_text_color(20, 20, 40)
        pdf.multi_cell(W() - 5, 6, _safe(f"시그널 {idx}. {signal.get('title', '')}"))
        pdf.set_x(x + 5)
        pdf.set_font("NG", "", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(W() - 5, 4.5, _safe(signal.get("evidence", "")))
        if item:
            pdf.set_x(x + 5)
            pdf.set_font("NG", "B", 8)
            pdf.set_text_color(42, 60, 100)
            pdf.multi_cell(
                W() - 5,
                4.5,
                _safe(
                    f"관련 보도자료 | {item.get('source', '')} | {item.get('title', '')[:65]}"
                ),
            )
        pdf.ln(5)

    pdf.add_page(); sec("02", "시그널 근거 데이터")
    for i, (cat, _) in enumerate(CAT_ORDER):
        ct = analysis["by_cat"].get(cat, 0)
        pdf.set_font("NG", "B", 9); pdf.set_text_color(*colors[i % len(colors)])
        pdf.cell(35, 6, CAT_NAMES.get(cat, cat))
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("NG", "", 8)
        pdf.cell(0, 6, f"{ct}건", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    body(f"주요 키워드: {' | '.join(f'#{kw}' for kw in top_kw)}", sz=9, b=True)
    pdf.ln(4)
    for cat, (src, item, _, news_cnt, _) in sorted(selected.items(), key=lambda x: -x[1][3]):
        body(
            f"{CAT_NAMES.get(cat, cat)} | {src} | 뉴스 인용 {news_cnt}건 | {_clean(item.get('title', ''))}",
            sz=8,
        )
        pdf.ln(1)

    pdf.set_draw_color(42, 60, 100); pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    body("본 리포트는 govbrief.kr이 정부 보도자료와 Google News RSS를 자동 분석하여 생성했습니다.", sz=7)

    out_dir = BASE_DIR / "data"
    out_path = out_dir / f"weekly-{target.isoformat()}.pdf"
    pdf.output(str(out_path))
    print(f"  [PDF] {out_path}")
    return out_path


# ═══════════════════════════════════════════════════════════
#  4. HTML 포스트 생성 (정적 사이트)
# ═══════════════════════════════════════════════════════════

def generate_weekly_post(analysis: dict, selected: dict, target: date) -> str:
    """주간 리포트 HTML 포스트 생성 → articles/weekly/{date}/index.html"""
    s = analysis["start"]
    e = analysis["end"]
    top_kw = [kw for kw, _ in analysis["keywords"].most_common(5)]
    signals = build_weekly_signals(analysis, selected)
    post_url = f"{SITE_URL}/policy/weekly/{target.isoformat()}/"

    h = _html.escape
    schedule_link = f"{SITE_URL}/articles/schedule/{target.isoformat()}/"
    signal_cards = ""
    for idx, signal in enumerate(signals, start=1):
        related_item = signal.get("related_item") or {}
        article_link = _article_link(
            related_item,
            {"ref": "weekly", "signal": str(idx)},
        ) if related_item else post_url
        source = h(related_item.get("source", "")) if related_item else "브리핑룸"
        related_title = h(signal.get("related_title", "")) if signal.get("related_title") else "관련 보도자료 준비 중"
        signal_cards += f"""
        <article class="signal-card">
          <div class="signal-index">Signal {idx:02d}</div>
          <h2>{h(signal.get("title", ""))}</h2>
          <p class="signal-evidence">{h(signal.get("evidence", ""))}</p>
          <div class="signal-related">
            <span>{source}</span>
            <a href="{article_link}">{related_title} →</a>
          </div>
        </article>"""

    evidence_rows = ""
    for cat, (src, item, _, ncnt, _) in sorted(selected.items(), key=lambda x: -x[1][3]):
        article_link = _article_link(item, {"ref": "weekly", "detail": "evidence", "cat": cat})
        evidence_rows += f"""
          <tr>
            <td>{h(CAT_NAMES.get(cat, cat))}</td>
            <td>{h(src)}</td>
            <td><a href="{article_link}">{h(_clean(item.get("title", "")))[:50]}</a></td>
            <td class="num">{ncnt}건</td>
          </tr>"""

    page_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>주간 정책 브리핑 ({s.month}/{s.day}~{e.month}/{e.day}) - 브리핑룸</title>
<meta name="description" content="대한민국 정부 주간 보도자료 분석 리포트 ({s} ~ {e})">
<link rel="canonical" href="{post_url}">
<meta property="og:type" content="article">
<meta property="og:title" content="주간 정책 브리핑 ({s.month}/{s.day}~{e.month}/{e.day})">
<meta property="og:url" content="{post_url}">
{SITE_FONT_LINKS}
<style>
{SITE_BASE_CSS}
.wrap{{max-width:960px;margin:0 auto;padding:24px 20px 72px}}
.back{{color:var(--m);text-decoration:none;font-size:13px;margin-bottom:24px;display:inline-block}}
{SITE_NAV_CSS}
h1{{font-family:var(--serif);font-size:34px;font-weight:700;margin-bottom:8px;letter-spacing:-.03em}}
.sub{{color:var(--t2);font-size:14px;margin-bottom:24px}}
.hero{{background:var(--s);color:var(--t);border:1px solid var(--b);border-radius:14px;padding:24px;margin-bottom:24px}}
.hero-kicker{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--m);margin-bottom:8px}}
.hero-copy{{font-size:15px;color:var(--t2);max-width:720px}}
.kpi{{display:flex;gap:16px;margin-bottom:24px}}
.kpi-box{{flex:1;background:var(--s);border:1px solid var(--b);border-radius:12px;padding:16px;text-align:center}}
.kpi-val{{font-size:24px;font-weight:700;color:var(--a)}}
.kpi-label{{font-size:11px;color:var(--m);margin-top:4px}}
.signals{{display:grid;gap:14px}}
.signal-card{{background:var(--s);border:1px solid var(--b);border-radius:16px;padding:22px;position:relative;overflow:hidden}}
.signal-card::before{{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--a)}}
.signal-index{{font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--m);margin-bottom:10px}}
.signal-card h2{{font-family:var(--serif);font-size:22px;line-height:1.4;margin-bottom:10px}}
.signal-evidence{{font-size:14px;color:var(--t2);margin-bottom:14px}}
.signal-related{{display:flex;align-items:center;justify-content:space-between;gap:16px;font-size:12px;color:var(--m);border-top:1px solid var(--b);padding-top:12px}}
.signal-related a{{color:var(--a);font-weight:600;text-decoration:none}}
.signal-related a:hover{{text-decoration:underline}}
.section{{margin-top:32px}}
.section h2{{font-family:var(--serif);font-size:18px;font-weight:700;border-bottom:2px solid var(--a);padding-bottom:6px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:var(--al);color:var(--a);font-weight:600;padding:8px 10px;text-align:left;border:1px solid var(--b)}}
td{{padding:7px 10px;border:1px solid var(--b);vertical-align:top}}
td a{{color:var(--a);text-decoration:none}}
td a:hover{{text-decoration:underline}}
td.num{{text-align:center;white-space:nowrap}}
.keywords{{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}}
.keywords span{{background:var(--a);color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:500}}
.footer{{margin-top:40px;padding-top:16px;border-top:1px solid var(--b);font-size:11px;color:var(--m);text-align:center}}
@media(max-width:600px){{.kpi{{flex-direction:column}}.wrap{{padding:16px 16px 64px}}h1{{font-size:26px}}.hero{{padding:18px}}.signal-card h2{{font-size:18px}}.signal-related{{flex-direction:column;align-items:flex-start}}}}
</style>
</head>
<body>
<div class="wrap">
{render_top_nav("weekly")}
<a class="back" href="/">← 브리핑룸으로</a>
<section class="hero">
  <div class="hero-kicker">Weekly Policy Signals</div>
  <h1>이번 주 정책 시그널 5개</h1>
  <div class="hero-copy">{s.year}년 {s.month}월 {s.day}일부터 {e.month}월 {e.day}일까지의 정부 보도자료 흐름을 Bloomberg형 데이터 밀도와 브리핑 형식으로 정리했습니다.</div>
</section>
<div class="sub">{s.year}년 {s.month}월 {s.day}일 ~ {e.month}월 {e.day}일</div>
{render_crosslinks((schedule_link, "차주 일정 보기"))}

<div class="kpi">
  <div class="kpi-box"><div class="kpi-val">{analysis['total']}</div><div class="kpi-label">총 보도자료</div></div>
  <div class="kpi-box"><div class="kpi-val">{analysis['sources_count']}</div><div class="kpi-label">참여 부처</div></div>
  <div class="kpi-box"><div class="kpi-val">{analysis['total'] - analysis['prev_total']:+d}</div><div class="kpi-label">전주 대비</div></div>
</div>

<div class="keywords">{''.join(f'<span>#{h(kw)}</span>' for kw in top_kw)}</div>

<div class="section">
  <h2>시그널 브리핑</h2>
  <div class="signals">{signal_cards}</div>
</div>

<div class="section">
  <h2>근거 데이터</h2>
  <table>
    <thead><tr><th>분야</th><th>부처</th><th>보도자료</th><th>뉴스</th></tr></thead>
    <tbody>{evidence_rows}</tbody>
  </table>
</div>

<div class="footer">
  govbrief.kr | 정부 보도자료 AI 분석 | {date.today()}
</div>
</div>
</body>
</html>"""

    out_dir = BASE_DIR / "policy" / "weekly" / target.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [HTML] {out_path}")
    return post_url


# ═══════════════════════════════════════════════════════════
#  5. 텔레그램 요약 메시지
# ═══════════════════════════════════════════════════════════

def format_weekly_telegram(analysis: dict, selected: dict, post_url: str, target: date) -> str:
    """주간 리포트를 텔레그램용 시그널 브리핑으로 요약"""
    s = analysis["start"]
    e = analysis["end"]
    top_kw = [kw for kw, _ in analysis["keywords"].most_common(5)]
    signals = build_weekly_signals(analysis, selected)

    lines = [
        f"📊 <b>이번 주 정책 시그널 5개 | {s.month}/{s.day}~{e.month}/{e.day}</b>",
        "",
        f"총 {analysis['total']}건 · {analysis['sources_count']}개 부처 · 전주 대비 {analysis['total'] - analysis['prev_total']:+d}건",
        f"키워드: {' '.join(f'#{kw}' for kw in top_kw)}",
        "",
        "━━━ 정책 시그널 ━━━",
        "",
    ]

    for idx, signal in enumerate(signals, start=1):
        item = signal.get("related_item") or {}
        link = _article_link(item, {"ref": "telegram", "detail": "weekly", "signal": str(idx)}) if item else post_url
        related_title = _escape_html(signal.get("related_title", "") or "관련 보도자료")
        lines.append(f"<b>{idx}. {_escape_html(signal.get('title', ''))}</b>")
        lines.append(f"  근거: {_escape_html(signal.get('evidence', ''))}")
        lines.append(f'  관련: <a href="{link}">{related_title}</a>')
        lines.append("")

    lines.append("")
    lines.append("──────────────────")
    lines.append(f'📄 <a href="{post_url}">전체 리포트 보기</a>')

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3950] + f'\n\n... <a href="{post_url}">더보기</a>'
    return text


# ═══════════════════════════════════════════════════════════
#  6. 메인 실행
# ═══════════════════════════════════════════════════════════

def run_weekly(target: date) -> bool:
    """주간 브리핑 전체 파이프라인"""
    import time as _time

    print(f"\n{'═' * 60}")
    print("[주간 브리핑 생성]")

    # 1. 분석
    print("  [1/5] 주간 데이터 분석...")
    analysis = analyze_weekly(target)
    if analysis["total"] == 0:
        print("  주간 데이터 없음 -> 스킵")
        return False
    print(f"  {analysis['start']} ~ {analysis['end']} | {analysis['total']}건")

    # 2. TOP 선정
    print("  [2/5] 분야별 TOP 1 선정 (뉴스 검색)...")
    selected = select_weekly_top(analysis)
    print(f"  {len(selected)}개 분야 선정 완료")

    # 3. PDF
    print("  [3/5] PDF 생성...")
    try:
        generate_pdf(analysis, selected, target)
    except Exception as ex:
        print(f"  PDF 생성 실패: {ex}")

    # 4. HTML 포스트
    print("  [4/5] HTML 포스트 생성...")
    post_url = generate_weekly_post(analysis, selected, target)
    print(f"  포스트 URL: {post_url}")

    # 5. 텔레그램
    print("  [5/5] 텔레그램 메시지...")
    msg = format_weekly_telegram(analysis, selected, post_url, target)
    print(f"  메시지 길이: {len(msg)}자")

    if TELEGRAM_ENABLED:
        send_telegram(msg)
    else:
        print("  [텔레그램] TELEGRAM_ENABLED=false -> 스킵")

    return True
