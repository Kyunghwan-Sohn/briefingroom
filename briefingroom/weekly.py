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
from briefingroom.llm import generate_weekly_signals, generate_weekly_report
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
    """주간 종합 보고서 HTML 생성 -> brief/weekly/{date}/index.html"""
    s = analysis["start"]
    e = analysis["end"]
    top_kw = [kw for kw, _ in analysis["keywords"].most_common(8)]
    signals = build_weekly_signals(analysis, selected)
    post_url = f"{SITE_URL}/brief/weekly/{target.isoformat()}/"
    h = _html.escape
    td = analysis["total"] - analysis["prev_total"]

    # LLM 종합 보고서 생성
    report_payload = {
        "period": {"start": s.isoformat(), "end": e.isoformat()},
        "totals": {"articles": analysis["total"], "sources": analysis["sources_count"], "prev_articles": analysis["prev_total"]},
        "by_category": analysis["by_cat"],
        "top_keywords": [{"keyword": kw, "count": cnt} for kw, cnt in analysis["keywords"].most_common(10)],
        "keyword_delta": analysis.get("kw_delta", {}),
        "signals": [{"title": sig.get("title", ""), "evidence": sig.get("evidence", "")} for sig in signals],
    }
    report = generate_weekly_report(report_payload)

    # 시그널 카드 HTML
    signal_cards = ""
    for idx, signal in enumerate(signals, start=1):
        related_item = signal.get("related_item") or {}
        article_link = _article_link(related_item, {"ref": "weekly", "signal": str(idx)}) if related_item else post_url
        source = h(related_item.get("source", "")) if related_item else ""
        related_title = h(signal.get("related_title", "")) if signal.get("related_title") else "관련 보도자료"
        signal_cards += f"""<div class="sig-card">
<div class="sig-top"><span class="sig-num">SIGNAL {idx:02d}</span><span class="sig-src">{source}</span></div>
<div class="sig-title">{h(signal.get("title", ""))}</div>
<div class="sig-evidence">{h(signal.get("evidence", ""))}</div>
<a class="sig-link" href="{article_link}">{related_title} &#8594;</a>
</div>\n"""

    # 분야별 동향 HTML
    sector_html = ""
    sector_colors = {"금융경제": "var(--sec)", "산업기술": "var(--green)", "사회복지": "var(--purple)", "외교안보": "var(--amber)", "행정법제": "var(--t3)"}
    for sector, desc in report.get("sectors", {}).items():
        color = sector_colors.get(sector, "var(--t3)")
        cnt = analysis["by_cat"].get(sector, 0)
        sector_html += f"""<div class="sector-card">
<div class="sector-hdr"><span class="sector-name" style="color:{color}">{h(sector)}</span><span class="sector-cnt">{cnt}건</span></div>
<div class="sector-body">{h(desc)}</div>
</div>\n"""

    # 핵심 수치 HTML
    figures_html = ""
    for fig in report.get("key_figures", [])[:5]:
        figures_html += f'<div class="fig"><div class="fig-val">{h(fig.get("value", ""))}</div><div class="fig-name">{h(fig.get("name", ""))}</div></div>\n'

    # 주요 보도자료 HTML
    top_articles = ""
    for cat, (src, item, _, ncnt, _) in sorted(selected.items(), key=lambda x: -x[1][3]):
        article_link = _article_link(item, {"ref": "weekly"})
        top_articles += f"""<a class="top-article" href="{article_link}">
<span class="ta-cat">{h(CAT_NAMES.get(cat, cat))}</span>
<span class="ta-title">{h(_clean(item.get("title", ""))[:60])}</span>
<span class="ta-src">{h(src)}</span>
</a>\n"""

    # 키워드 태그
    kw_tags = "".join(f'<span class="kw-tag">{h(kw)}</span>' for kw in top_kw)

    page_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>주간 정책 보고서 ({s.month}/{s.day}~{e.month}/{e.day}) - 브리핑룸</title>
<meta name="description" content="정부 보도자료 {analysis['total']}건을 AI가 종합 분석한 주간 보고서">
<link rel="canonical" href="{post_url}">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<script>(function(){{if(/Mobi|Android|iPhone/i.test(navigator.userAgent))document.documentElement.classList.add('is-mobile')}})();</script>
<style>
*{{box-sizing:border-box;margin:0;padding:0;word-break:keep-all}}
:root{{--bg:#f7f7f5;--s:#fff;--b:#dcdcd8;--bl:#ededea;--t:#1a1a1a;--t2:#555;--t3:#888;--m:#bbb;--sec:#1e40af;--sec-bg:#eff6ff;--sec-border:#bfdbfe;--red:#dc2626;--red-bg:#fee2e2;--amber:#d97706;--amber-bg:#fef3c7;--green:#047857;--green-bg:#ecfdf5;--purple:#7c3aed;--purple-bg:#f5f3ff;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}}
body{{background:var(--bg);color:var(--t);font-family:var(--sans);font-size:16px;line-height:1.7;min-width:1120px}}
.is-mobile body{{min-width:0;font-size:15px;padding-bottom:68px}}
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
.hero{{background:linear-gradient(180deg,var(--sec-bg),#fff);border-bottom:1px solid var(--sec-border);padding:40px 32px 32px}}
.hero-inner{{max-width:1080px;margin:0 auto}}
.hero-bc{{font-size:12px;color:var(--t3);margin-bottom:14px}}
.hero-bc a{{color:var(--sec);text-decoration:none;font-weight:600}}
.hero-bc span{{margin:0 6px;color:var(--m)}}
.hero-ey{{font-family:var(--mono);font-size:11px;color:var(--sec);font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px}}
.hero-title{{font-family:var(--serif);font-size:30px;font-weight:700;margin-bottom:6px}}
.hero-sub{{font-size:14px;color:var(--t2);line-height:1.7;max-width:640px;margin-bottom:20px}}
.hero-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;max-width:720px}}
.hs{{background:#fff;border:1px solid var(--sec-border);border-radius:8px;padding:12px 14px}}
.hs .hl{{font-size:10px;color:var(--sec);font-weight:700}}
.hs .hn{{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--sec);line-height:1.1;margin-top:3px}}
.hs .hu{{font-family:var(--sans);font-size:11px;font-weight:600;color:var(--t3)}}
.is-mobile .hero{{padding:20px 16px}}
.is-mobile .hero-title{{font-size:22px}}
.is-mobile .hero-stats{{grid-template-columns:repeat(2,1fr)}}
.shell{{max-width:1080px;margin:0 auto;padding:24px 16px 40px}}
.sec-hdr{{font-family:var(--serif);font-size:22px;font-weight:700;display:flex;align-items:center;gap:10px;margin:28px 0 14px}}
.sec-hdr::before{{content:'';width:3px;height:18px;background:var(--sec);border-radius:1px}}
.summary-box{{background:var(--sec-bg);border-left:4px solid var(--sec);border-radius:0 10px 10px 0;padding:20px 24px;margin-bottom:20px;font-size:17px;color:var(--t);line-height:1.9}}
.kw-row{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:20px}}
.kw-tag{{font-size:13px;font-weight:600;padding:5px 12px;border-radius:10px;border:1px solid var(--sec-border);color:var(--sec)}}
.fig-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:20px}}
.fig{{background:#fff;border:1px solid var(--b);border-radius:10px;padding:16px;text-align:center}}
.fig-val{{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--sec)}}
.fig-name{{font-size:12px;color:var(--t3);margin-top:4px}}
.sig-card{{background:#fff;border:1px solid var(--b);border-radius:10px;padding:20px 22px;margin-bottom:10px;border-left:3px solid var(--sec)}}
.sig-top{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.sig-num{{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--sec);background:var(--sec-bg);padding:3px 8px;border-radius:4px}}
.sig-src{{font-size:12px;color:var(--t3);font-weight:600}}
.sig-title{{font-family:var(--serif);font-size:18px;font-weight:700;line-height:1.4;margin-bottom:8px}}
.sig-evidence{{font-size:15px;color:var(--t2);line-height:1.8;margin-bottom:8px}}
.sig-link{{font-size:13px;color:var(--sec);font-weight:600;text-decoration:none}}
.sig-link:hover{{text-decoration:underline}}
.sector-card{{background:#fff;border:1px solid var(--b);border-radius:10px;padding:18px 22px;margin-bottom:10px}}
.sector-hdr{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.sector-name{{font-family:var(--serif);font-size:16px;font-weight:700}}
.sector-cnt{{font-family:var(--mono);font-size:12px;color:var(--sec);font-weight:700}}
.sector-body{{font-size:15px;color:var(--t2);line-height:1.8}}
.analysis-box{{background:#fff;border:1px solid var(--b);border-radius:10px;padding:20px 24px;margin-bottom:16px}}
.analysis-label{{font-family:var(--sans);font-size:15px;font-weight:700;margin-bottom:8px}}
.analysis-label-cmp{{color:var(--sec)}}
.analysis-label-out{{color:var(--amber)}}
.analysis-body{{font-size:16px;color:var(--t2);line-height:1.9;border-left:4px solid var(--sec);background:var(--sec-bg);border-radius:0 10px 10px 0;padding:16px 20px}}
.analysis-body-out{{border-left-color:var(--amber);background:var(--amber-bg)}}
.top-article{{display:flex;align-items:center;gap:8px;padding:10px 0;border-top:1px dashed var(--bl);text-decoration:none;color:var(--t);font-size:14px}}
.top-article:first-child{{border-top:none}}
.top-article:hover{{color:var(--sec)}}
.ta-cat{{font-size:11px;font-weight:600;padding:2px 8px;border-radius:4px;background:var(--sec-bg);color:var(--sec);flex-shrink:0}}
.ta-title{{flex:1;font-weight:600;line-height:1.4}}
.ta-src{{font-size:11px;color:var(--t3);flex-shrink:0}}
.footer{{max-width:1080px;margin:20px auto 0;padding:24px 16px;text-align:center;color:var(--t3);border-top:1px solid var(--bl)}}
.footer-motto{{font-family:var(--serif);font-size:14px;color:var(--t2)}}
.footer-site{{font-family:var(--mono);font-size:11px;color:var(--t3);margin-top:4px}}
.bnav{{display:none}}
.is-mobile .bnav{{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;bottom:0;left:0;right:0;z-index:200;background:#fff;border-top:1px solid var(--b);padding:8px 0 calc(10px + env(safe-area-inset-bottom))}}
.bnav a{{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--t3);font-size:10.5px;font-weight:600}}
.bnav a.on{{color:var(--sec)}}
</style>
</head>
<body>
<header class="hdr">
  <a class="hdr-logo" href="/">브리핑룸</a>
  <nav class="hdr-nav">
    <a href="/"><span class="lbl-full">홈</span><span class="lbl-short">홈</span></a>
    <a class="on" href="/brief/"><span class="lbl-full">정부 발표</span><span class="lbl-short">정부 발표</span></a>
    <a href="/keywords/"><span class="lbl-full">키워드 트렌드</span><span class="lbl-short">키워드</span></a>
    <a href="/regulation/"><span class="lbl-full">금융/부동산 규제</span><span class="lbl-short">금융/부동산</span></a>
  </nav>
</header>
<section class="hero">
  <div class="hero-inner">
    <div class="hero-bc"><a href="/brief/">정부 발표</a><span>/</span>주간 정책 보고서</div>
    <div class="hero-ey">WEEKLY POLICY REPORT</div>
    <h1 class="hero-title">{s.month}월 {s.day}일 ~ {e.month}월 {e.day}일 주간 정책 보고서</h1>
    <p class="hero-sub">{analysis['total']}건의 정부 보도자료를 AI가 종합 분석한 주간 보고서입니다.</p>
    <div class="hero-stats">
      <div class="hs"><div class="hl">총 보도자료</div><div class="hn">{analysis['total']}<span class="hu">건</span></div></div>
      <div class="hs"><div class="hl">참여 부처</div><div class="hn">{analysis['sources_count']}<span class="hu">개</span></div></div>
      <div class="hs"><div class="hl">전주 대비</div><div class="hn">{td:+d}<span class="hu">건</span></div></div>
      <div class="hs"><div class="hl">정책 시그널</div><div class="hn">{len(signals)}<span class="hu">개</span></div></div>
    </div>
  </div>
</section>
<div class="shell">

  <div class="sec-hdr">주간 종합 요약</div>
  <div class="summary-box">{h(report.get("summary", "이번 주 정부 보도자료를 종합 분석 중입니다."))}</div>

  <div class="kw-row">{kw_tags}</div>

  {"<div class='sec-hdr'>핵심 수치</div><div class='fig-row'>" + figures_html + "</div>" if figures_html else ""}

  <div class="sec-hdr">정책 시그널</div>
  {signal_cards}

  {"<div class='sec-hdr'>분야별 동향</div>" + sector_html if sector_html else ""}

  {"<div class='sec-hdr'>전주 대비 변화</div><div class='analysis-box'><div class='analysis-label analysis-label-cmp'>COMPARED TO LAST WEEK</div><div class='analysis-body'>" + h(report.get("comparison", "")) + "</div></div>" if report.get("comparison") else ""}

  {"<div class='sec-hdr'>향후 전망</div><div class='analysis-box'><div class='analysis-label analysis-label-out'>OUTLOOK</div><div class='analysis-body analysis-body-out'>" + h(report.get("outlook", "")) + "</div></div>" if report.get("outlook") else ""}

  <div class="sec-hdr">주요 보도자료</div>
  <div style="background:#fff;border:1px solid var(--b);border-radius:10px;padding:16px 20px;margin-bottom:16px">
    {top_articles}
  </div>

</div>
<footer class="footer">
  <div class="footer-motto">정부 정책과 금융/부동산 규제, 한 화면에</div>
  <div class="footer-site">govbrief.kr</div>
</footer>
<nav class="bnav">
  <a href="/">홈</a><a class="on" href="/brief/">정부 발표</a><a href="/keywords/">키워드</a><a href="/regulation/">금융/부동산</a>
</nav>
</body>
</html>"""

    brief_dir = BASE_DIR / "brief" / "weekly" / target.isoformat()
    brief_dir.mkdir(parents=True, exist_ok=True)
    brief_path = brief_dir / "index.html"
    brief_path.write_text(page_html, encoding="utf-8")
    print(f"  [Weekly Report] {brief_path}")
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
