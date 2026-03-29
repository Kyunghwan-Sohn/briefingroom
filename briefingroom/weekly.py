"""주간 정책 브리핑 — 분석 + PDF + HTML 포스트 + 텔레그램 요약

McKinsey/BCG 스타일 애널리스트 리포트 자동 생성.
매주 일요일 10:00 KST 실행.
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from briefingroom.config import BASE_DIR, CAT_MAP, DATA_DIR
from briefingroom.telegram import (
    CAT_ORDER, SITE_URL, _escape_html, send_telegram,
    TELEGRAM_ENABLED,
)

ARTICLES_DIR = BASE_DIR / "articles"

# ═══════════════════════════════════════════════════════════
#  1. 데이터 분석
# ═══════════════════════════════════════════════════════════

def _get_week_range(target: date) -> tuple[date, date]:
    """target 기준 직전 월~토 날짜 범위"""
    end = target - timedelta(days=1)
    start = end - timedelta(days=6)
    return start, end


def _load_items_from_json(start: date, end: date) -> list[dict]:
    """data/ 디렉토리의 JSON 파일에서 기간 내 아이템 로드"""
    items = []
    d = start
    while d <= end:
        json_path = DATA_DIR / f"{d.isoformat()}.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                for it in data.get("items", []):
                    # keywords가 리스트면 쉼표 구분 문자열로 변환
                    kw = it.get("keywords", "")
                    if isinstance(kw, list):
                        kw = ", ".join(kw)
                    items.append({
                        "source": it.get("source", ""),
                        "title": it.get("title", ""),
                        "url": it.get("url", ""),
                        "date": it.get("date", d.isoformat()),
                        "category": it.get("category", "") or CAT_MAP.get(it.get("source", ""), "행정법제"),
                        "summary": it.get("summary", ""),
                        "keywords": kw,
                    })
            except Exception as e:
                print(f"  [JSON] {json_path.name} 로드 실패: {e}")
        d += timedelta(days=1)
    return items


def analyze_weekly(target: date) -> dict:
    """data/ JSON 파일에서 7일 + 전주 7일 집계"""
    start, end = _get_week_range(target)
    prev_start = start - timedelta(days=7)
    prev_end = start - timedelta(days=1)

    rows = _load_items_from_json(start, end)
    prev_rows = _load_items_from_json(prev_start, prev_end)

    total = len(rows)
    by_cat = Counter()
    by_source = Counter()
    keywords = Counter()
    items_by_cat = defaultdict(list)

    for r in rows:
        cat = r["category"] or CAT_MAP.get(r["source"], "행정법제")
        by_cat[cat] += 1
        by_source[r["source"]] += 1
        items_by_cat[cat].append(r)
        if r["keywords"]:
            for kw in r["keywords"].split(","):
                kw = kw.strip()
                if kw and len(kw) > 1:
                    keywords[kw] += 1

    prev_total = len(prev_rows)
    prev_keywords = Counter()
    for r in prev_rows:
        if r.get("keywords"):
            for kw in r["keywords"].split(","):
                kw = kw.strip()
                if kw and len(kw) > 1:
                    prev_keywords[kw] += 1

    kw_delta = {}
    for kw, cnt in keywords.most_common(30):
        prev_cnt = prev_keywords.get(kw, 0)
        pct = ((cnt - prev_cnt) / prev_cnt * 100) if prev_cnt > 0 else 999
        kw_delta[kw] = {"count": cnt, "prev": prev_cnt, "change_pct": pct}

    return {
        "start": start, "end": end,
        "total": total, "prev_total": prev_total,
        "by_cat": dict(by_cat), "by_source": by_source,
        "keywords": keywords, "kw_delta": kw_delta,
        "items_by_cat": items_by_cat,
        "sources_count": len(by_source),
    }


def select_weekly_top(analysis: dict) -> dict:
    """분야별 TOP 1 — Google News RSS 기사 수 기반"""
    from briefingroom.news import search_related_news
    import time as _time

    selected = {}
    for cat, emoji in CAT_ORDER:
        items = analysis["items_by_cat"].get(cat, [])
        if not items:
            continue

        candidates = [it for it in items
                      if it.get("summary") and not it["summary"].startswith("[")]
        if not candidates:
            candidates = items[:5]

        by_source = defaultdict(list)
        for it in candidates:
            by_source[it["source"]].append(it)

        source_tops = sorted(
            [(src, lst[0], len(lst)) for src, lst in by_source.items()],
            key=lambda x: -x[2],
        )

        best = None
        best_news = -1
        for src, item, cnt in source_tops[:5]:
            articles = search_related_news(item["title"], src, max_results=100)
            n = len(articles)
            print(f"    [{cat}] {src}: \"{item['title'][:30]}...\" -> 뉴스 {n}건")
            if n > best_news:
                best_news = n
                best = (src, item, cnt, n, articles[:2])
            _time.sleep(0.3)

        if best:
            selected[cat] = best

    return selected


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
    """McKinsey/BCG 스타일 주간 리포트 PDF 생성"""
    from fpdf import FPDF

    reg, bold = _ensure_fonts()
    s = analysis["start"]
    e = analysis["end"]
    top_kw = [kw for kw, _ in analysis["keywords"].most_common(5)]
    colors = [(47, 84, 235), (220, 38, 38), (22, 163, 74), (124, 58, 237), (217, 119, 6)]

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

    def insight(text):
        pdf.set_fill_color(245, 247, 252)
        pdf.set_draw_color(42, 60, 100); pdf.set_line_width(1.5)
        y = pdf.get_y(); x = pdf.l_margin
        pdf.line(x, y, x, y + 12)
        pdf.set_x(x + 4)
        pdf.set_font("NG", "", 8); pdf.set_text_color(42, 60, 100)
        pdf.multi_cell(W() - 4, 4.5, _safe(text), fill=True)
        pdf.set_text_color(40, 40, 40)
        pdf.ln(2)

    def table_header(cols):
        pdf.set_font("NG", "B", 8); pdf.set_fill_color(235, 240, 250)
        for label, w in cols:
            pdf.cell(w, 6, label, border=1, fill=True, align="C")
        pdf.ln()

    def table_row(cells):
        pdf.set_font("NG", "", 8)
        for text, w, align in cells:
            pdf.cell(w, 5.5, _safe(text), border=1, align=align)
        pdf.ln()

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

    # -- EXECUTIVE SUMMARY --
    pdf.add_page(); sec("01", "Executive Summary")
    td = analysis["total"] - analysis["prev_total"]
    y0 = pdf.get_y()
    for i, (l, v) in enumerate([("총 보도자료", f"{analysis['total']}건"),
                                 ("참여 부처", f"{analysis['sources_count']}개"),
                                 ("5대 분야", "경제/사회/산업/외교/행정")]):
        x = pdf.l_margin + i * 45
        pdf.set_xy(x, y0); pdf.set_font("NG", "", 7); pdf.set_text_color(120, 120, 120)
        pdf.cell(45, 4, l)
        pdf.set_xy(x, y0 + 4); pdf.set_font("NG", "B", 14); pdf.set_text_color(42, 60, 100)
        pdf.cell(45, 8, v)
    pdf.set_y(y0 + 18); pdf.ln(3)
    body(f"핵심 키워드:  {'  |  '.join(f'#{kw}' for kw in top_kw)}", sz=9, b=True)
    pdf.ln(4)

    # 분석 코멘트 — 데이터 기반 자동 생성
    top_cat = max(analysis["by_cat"], key=analysis["by_cat"].get) if analysis["by_cat"] else ""
    top_cat_cnt = analysis["by_cat"].get(top_cat, 0)
    news_sorted = sorted(selected.items(), key=lambda x: -x[1][3])
    top_news_cat, (top_news_src, _, _, top_news_cnt, _) = news_sorted[0] if news_sorted else ("", ("", {}, 0, 0, []))

    body(f"금주 정부 보도자료 {analysis['total']}건을 분석한 결과, "
         f"{CAT_NAMES.get(top_cat, top_cat)} 분야가 {top_cat_cnt}건으로 가장 활발했다. "
         f"언론 반응 측면에서는 {top_news_src}의 보도자료가 {top_news_cnt}건의 뉴스 인용으로 "
         f"가장 높은 미디어 임팩트를 기록했다.")
    pdf.ln(5)

    # -- SECTOR DEEP-DIVE --
    pdf.add_page(); sec("02", "Sector Deep-Dive")
    total = analysis["total"] or 1

    # 비중 바차트
    pdf.set_font("NG", "B", 9); pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, "분야별 정책 활동 비중", new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)
    for i, (cat, _) in enumerate(CAT_ORDER):
        ct = analysis["by_cat"].get(cat, 0)
        r = ct / total
        pdf.set_font("NG", "", 8); pdf.set_text_color(80, 80, 80)
        pdf.cell(30, 5, CAT_NAMES.get(cat, cat))
        y = pdf.get_y(); x = pdf.l_margin + 30
        pdf.set_fill_color(*colors[i])
        pdf.rect(x, y + 0.5, r * 100, 4, style="F")
        pdf.set_xy(x + r * 100 + 2, y)
        pdf.set_font("NG", "B", 8)
        pdf.cell(20, 5, f"{ct}건 ({r * 100:.0f}%)")
        pdf.ln(6)
    pdf.ln(5)

    # 분야별 Top Story + 링크
    for i, (cat, _) in enumerate(CAT_ORDER):
        if cat not in selected:
            continue
        src, item, cnt, news_cnt, _ = selected[cat]
        title = _safe(_clean(item.get("title", "")))[:60]
        summary = _safe(_get_summary(item))
        url = item.get("url", "")

        pdf.set_font("NG", "B", 11)
        pdf.set_text_color(*colors[i])
        pdf.cell(0, 7, f"{CAT_NAMES.get(cat, cat)}  ({analysis['by_cat'].get(cat, 0)}건)",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("NG", "B", 9)
        pdf.cell(0, 5, f"Top Story  |  {src}  |  뉴스 인용 {news_cnt}건",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("NG", "", 8)
        pdf.cell(0, 5, f"  {title}", new_x="LMARGIN", new_y="NEXT")
        if summary:
            body(f"  {summary}", sz=8)
        if url:
            pdf.set_font("NG", "", 7); pdf.set_text_color(42, 60, 100)
            pdf.cell(0, 4, f"  -> {url[:80]}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(40, 40, 40)
        pdf.ln(4)

    # -- MEDIA & KEYWORDS --
    pdf.add_page(); sec("03", "Media Impact & Keyword Trends")
    pdf.set_font("NG", "B", 10); pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 7, "뉴스 인용 TOP 5 보도자료", new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)

    cols = [("분야", 25), ("부처", 25), ("보도자료 제목", 75), ("뉴스", 15), ("링크", 20)]
    table_header(cols)
    all_sel = sorted(selected.items(), key=lambda x: -x[1][3])
    for cat, (src, item, _, ncnt, _) in all_sel:
        title = _safe(_clean(item.get("title", "")))[:40]
        url = item.get("url", "")
        short_url = "원문" if url else ""
        table_row([(CAT_NAMES.get(cat, cat), 25, "C"), (src, 25, "C"),
                   (f" {title}", 75, "L"), (f"{ncnt}건", 15, "C"), (short_url, 20, "C")])

    pdf.ln(5)
    pdf.set_font("NG", "B", 10); pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 7, "정책 키워드 트렌드", new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)

    rising = [(kw, d) for kw, d in analysis["kw_delta"].items()
              if d["change_pct"] >= 50 and d["count"] >= 3]
    rising.sort(key=lambda x: -x[1]["count"])
    all_items = [it for ci in analysis["items_by_cat"].values() for it in ci]

    if rising:
        cols2 = [("키워드", 35), ("횟수", 15), ("주요 관련 부처", 110)]
        table_header(cols2)
        for kw, d in rising[:8]:
            sources = Counter()
            for it in all_items:
                if it.get("keywords") and kw in it["keywords"]:
                    sources[it["source"]] += 1
            ss = ", ".join(f"{s}({c})" for s, c in sources.most_common(3))
            table_row([(f" #{kw}", 35, "L"), (f"{d['count']}회", 15, "C"), (f" {ss}", 110, "L")])

    # -- IMPLICATIONS --
    pdf.add_page(); sec("04", "Implications & Outlook")
    pdf.ln(3)

    # 데이터 기반 시사점 자동 생성
    body("1. 주요 정책 테마", sz=11, b=True); pdf.ln(1)
    kw_str = ", ".join(f"'{kw}'" for kw in top_kw[:3])
    body(f"이번 주 핵심 키워드({kw_str})는 정부 정책의 현재 우선순위를 반영한다. "
         f"특히 '{top_kw[0]}'이 {analysis['keywords'].most_common(1)[0][1]}회 등장하며 "
         f"범부처 차원의 정책 흐름으로 자리잡고 있다.")
    pdf.ln(4)

    body("2. 미디어 임팩트 분석", sz=11, b=True); pdf.ln(1)
    body(f"뉴스 인용 상위 보도자료는 국민 생활 밀착형 정책일수록 언론 관심도가 높은 경향을 보였다. "
         f"{top_news_src}({top_news_cnt}건)의 사례는 정책 커뮤니케이션에서 '체감형' 메시지의 "
         f"미디어 확산 효과를 시사한다.")
    pdf.ln(4)

    body("3. 다음 주 관전 포인트", sz=11, b=True); pdf.ln(1)
    body(f"금주 신규 등장한 키워드와 급상승 이슈의 후속 정책 발표 여부, "
         f"그리고 {CAT_NAMES.get(top_cat, top_cat)} 분야의 정책 연속성을 주목할 필요가 있다.")
    pdf.ln(6)

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
    post_url = f"{SITE_URL}/articles/weekly/{target.isoformat()}/"

    h = _html.escape

    # 분야별 Top Story 행
    sector_rows = ""
    for cat, _ in CAT_ORDER:
        if cat not in selected:
            continue
        src, item, cnt, news_cnt, _ = selected[cat]
        title = h(_clean(item.get("title", "")))[:60]
        summary = h(_get_summary(item))
        d = item.get("date", "")
        article_link = f"{SITE_URL}/articles/{d}/000/" if d else SITE_URL
        cat_total = analysis["by_cat"].get(cat, 0)

        sector_rows += f"""
        <div class="sector-card">
          <div class="sector-header">{h(CAT_NAMES.get(cat, cat))} ({cat_total}건)</div>
          <div class="sector-source">{h(src)} | 뉴스 인용 {news_cnt}건</div>
          <div class="sector-title"><a href="{article_link}">{title}</a></div>
          <div class="sector-summary">{summary}</div>
        </div>"""

    # 뉴스 인용 TOP 5 테이블
    news_rows = ""
    for cat, (src, item, _, ncnt, _) in sorted(selected.items(), key=lambda x: -x[1][3]):
        title = h(_clean(item.get("title", "")))[:50]
        d = item.get("date", "")
        article_link = f"{SITE_URL}/articles/{d}/000/" if d else SITE_URL
        news_rows += f"""
          <tr>
            <td>{h(CAT_NAMES.get(cat, cat))}</td>
            <td>{h(src)}</td>
            <td><a href="{article_link}">{title}</a></td>
            <td class="num">{ncnt}건</td>
          </tr>"""

    # 키워드 테이블
    all_items = [it for ci in analysis["items_by_cat"].values() for it in ci]
    rising = [(kw, d) for kw, d in analysis["kw_delta"].items()
              if d["change_pct"] >= 50 and d["count"] >= 3]
    rising.sort(key=lambda x: -x[1]["count"])

    kw_rows = ""
    for kw, d in rising[:8]:
        sources = Counter()
        for it in all_items:
            if it.get("keywords") and kw in it["keywords"]:
                sources[it["source"]] += 1
        ss = ", ".join(f"{s}({c})" for s, c in sources.most_common(3))
        pct = "신규" if d["prev"] == 0 else f"+{d['change_pct']:.0f}%"
        kw_rows += f"<tr><td>#{h(kw)}</td><td class='num'>{d['count']}회</td><td>{pct}</td><td>{h(ss)}</td></tr>"

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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&family=Pretendard:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#f5f4f0;--surface:#fff;--border:#e0ddd7;--text:#1c1b18;--text2:#4a4844;--accent:#2a3c64;--accent-l:#eef0fd}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Pretendard',sans-serif;line-height:1.7}}
.wrap{{max-width:780px;margin:0 auto;padding:32px 24px}}
.back{{color:#96938c;text-decoration:none;font-size:13px;margin-bottom:24px;display:inline-block}}
h1{{font-family:'Noto Serif KR',serif;font-size:28px;font-weight:700;margin-bottom:8px}}
.sub{{color:var(--text2);font-size:14px;margin-bottom:24px}}
.kpi{{display:flex;gap:16px;margin-bottom:24px}}
.kpi-box{{flex:1;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;text-align:center}}
.kpi-val{{font-size:24px;font-weight:700;color:var(--accent)}}
.kpi-label{{font-size:11px;color:#96938c;margin-top:4px}}
.section{{margin-top:32px}}
.section h2{{font-family:'Noto Serif KR',serif;font-size:18px;font-weight:700;border-bottom:2px solid var(--accent);padding-bottom:6px;margin-bottom:16px}}
.sector-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px}}
.sector-header{{font-weight:700;font-size:15px;color:var(--accent);margin-bottom:4px}}
.sector-source{{font-size:12px;color:#96938c;margin-bottom:6px}}
.sector-title a{{color:var(--text);font-weight:600;font-size:14px;text-decoration:none}}
.sector-title a:hover{{color:var(--accent);text-decoration:underline}}
.sector-summary{{font-size:13px;color:var(--text2);margin-top:6px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:var(--accent-l);color:var(--accent);font-weight:600;padding:8px 10px;text-align:left;border:1px solid var(--border)}}
td{{padding:7px 10px;border:1px solid var(--border);vertical-align:top}}
td a{{color:var(--accent);text-decoration:none}}
td a:hover{{text-decoration:underline}}
td.num{{text-align:center;white-space:nowrap}}
.insight{{background:var(--accent-l);border-left:4px solid var(--accent);padding:12px 16px;margin:16px 0;font-size:13px;color:var(--accent);border-radius:0 8px 8px 0}}
.keywords{{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}}
.keywords span{{background:var(--accent);color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:500}}
.footer{{margin-top:40px;padding-top:16px;border-top:1px solid var(--border);font-size:11px;color:#96938c;text-align:center}}
@media(max-width:600px){{.kpi{{flex-direction:column}}.wrap{{padding:20px 16px}}h1{{font-size:22px}}}}
</style>
</head>
<body>
<div class="wrap">
<a class="back" href="/">← 브리핑룸으로</a>
<h1>주간 정책 브리핑</h1>
<div class="sub">{s.year}년 {s.month}월 {s.day}일 ~ {e.month}월 {e.day}일</div>

<div class="kpi">
  <div class="kpi-box"><div class="kpi-val">{analysis['total']}</div><div class="kpi-label">총 보도자료</div></div>
  <div class="kpi-box"><div class="kpi-val">{analysis['sources_count']}</div><div class="kpi-label">참여 부처</div></div>
  <div class="kpi-box"><div class="kpi-val">{'#' + top_kw[0] if top_kw else '-'}</div><div class="kpi-label">핵심 키워드</div></div>
</div>

<div class="keywords">{''.join(f'<span>#{h(kw)}</span>' for kw in top_kw)}</div>

<div class="section">
  <h2>분야별 Top Story</h2>
  {sector_rows}
</div>

<div class="section">
  <h2>뉴스 인용 TOP 5</h2>
  <table>
    <thead><tr><th>분야</th><th>부처</th><th>보도자료</th><th>뉴스</th></tr></thead>
    <tbody>{news_rows}</tbody>
  </table>
</div>

<div class="section">
  <h2>정책 키워드 트렌드</h2>
  <table>
    <thead><tr><th>키워드</th><th>횟수</th><th>변화</th><th>관련 부처</th></tr></thead>
    <tbody>{kw_rows}</tbody>
  </table>
</div>

<div class="footer">
  govbrief.kr | 정부 보도자료 AI 분석 | {date.today()}
</div>
</div>
</body>
</html>"""

    out_dir = ARTICLES_DIR / "weekly" / target.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [HTML] {out_path}")
    return post_url


# ═══════════════════════════════════════════════════════════
#  5. 텔레그램 요약 메시지
# ═══════════════════════════════════════════════════════════

def format_weekly_telegram(analysis: dict, selected: dict, post_url: str, target: date) -> str:
    """5페이지 리포트를 텔레그램용으로 압축 요약"""
    s = analysis["start"]
    e = analysis["end"]
    top_kw = [kw for kw, _ in analysis["keywords"].most_common(5)]

    lines = [
        f"📊 <b>주간 정책 브리핑 | {s.month}/{s.day}~{e.month}/{e.day}</b>",
        "",
        f"총 {analysis['total']}건 · {analysis['sources_count']}개 부처",
        f"키워드: {' '.join(f'#{kw}' for kw in top_kw)}",
        "",
        "━━━ 분야별 Top Story ━━━",
        "",
    ]

    for cat, _ in CAT_ORDER:
        if cat not in selected:
            continue
        src, item, cnt, news_cnt, _ = selected[cat]
        title = _escape_html(_clean(item.get("title", "")))[:45]
        d = item.get("date", "")
        article_link = f"{SITE_URL}/articles/{d}/000/" if d else SITE_URL
        cat_name = CAT_NAMES.get(cat, cat)

        lines.append(f"<b>{cat_name}</b> | {_escape_html(src)} | 📰 {news_cnt}건")
        lines.append(f'  ▸ <a href="{article_link}">{title}</a>')
        lines.append("")

    lines.append("━━━ 키워드 트렌드 ━━━")
    lines.append("")

    rising = [(kw, d) for kw, d in analysis["kw_delta"].items()
              if d["change_pct"] >= 50 and d["count"] >= 3]
    rising.sort(key=lambda x: -x[1]["count"])
    for kw, d in rising[:5]:
        pct = "신규" if d["prev"] == 0 else f"+{d['change_pct']:.0f}%"
        lines.append(f"  #{_escape_html(kw)} ({d['count']}회, {pct})")

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
