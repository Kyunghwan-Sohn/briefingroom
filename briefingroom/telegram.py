"""텔레그램 일일/주간 브리핑 발송

일일: 오전/오후 당일 보도자료 종합 → 분야별 대표 1~2건
주간: 일요일 오전 7일간 보도자료 통계 + 트렌드 분석
"""
from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

import requests

from briefingroom.config import CAT_MAP
from briefingroom.weekly_analysis import analyze_weekly, select_weekly_top

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = os.environ.get("TELEGRAM_ENABLED", "true").lower() in ("true", "1", "yes")

SITE_URL = "https://govbrief.kr"

# 분야 순서 + 이모지
CAT_ORDER = [
    ("금융경제", "💰"),
    ("사회복지", "🏥"),
    ("산업기술", "⚙️"),
    ("외교안보", "🌏"),
    ("행정법제", "📜"),
]

DAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]


def _escape_html(text: str) -> str:
    """텔레그램 HTML 특수문자 이스케이프"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _article_url(item: dict, all_items: list[dict] = None) -> str:
    """govbrief.kr 상세 페이지 URL 생성"""
    d = item.get("date", "")
    if not d:
        return SITE_URL
    slug = item.get("slug", "")
    if slug:
        return f"{SITE_URL}/articles/{d}/{slug}/"
    # 같은 날짜 아이템 목록에서 인덱스 찾기
    if all_items:
        same_date = [it for it in all_items if it.get("date") == d]
        try:
            idx = same_date.index(item)
        except ValueError:
            idx = 0
    else:
        idx = 0
    return f"{SITE_URL}/articles/{d}/{idx:03d}/"


def _append_query(url: str, **params: str) -> str:
    from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        if value:
            query[key] = value
    return urlunparse(parsed._replace(query=urlencode(query)))


def _split_telegram_html(text: str, limit: int = 4096) -> list[str]:
    """HTML 태그를 깨지 않도록 메시지를 분할한다."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n", 0, limit - 32)
        if split_at < 0:
            split_at = limit - 32

        candidate = remaining[:split_at].rstrip()
        if not candidate:
            candidate = remaining[: limit - 32].rstrip()

        chunks.append(_fix_html(candidate))
        remaining = remaining[len(candidate):].lstrip()

    return chunks


# 분야별 필수 포함 부처
MUST_INCLUDE = {
    "금융경제": ["금융위원회"],
    "산업기술": ["국토교통부"],
    "행정법제": [],
    "사회복지": [],
    "외교안보": [],
}
# 전체 필수 부처 (어떤 분야든 반드시 포함)
PRIORITY_SOURCES = ["금융위원회", "국토교통부", "산업통상자원부", "산업통상부"]


def select_top_articles(items: list[dict], max_per_cat: int = 3) -> dict:
    """분야별 대표 보도자료 선정 — 필수 부처 우선 + 뉴스 기사 많은 건"""
    by_cat = defaultdict(list)
    for item in items:
        cat = CAT_MAP.get(item.get("source", ""), "행정법제")
        by_cat[cat].append(item)

    selected = {}
    for cat, cat_items in by_cat.items():
        # 부처별 그룹핑
        by_source = defaultdict(list)
        for item in cat_items:
            by_source[item["source"]].append(item)

        # 부처별 대표 1건 선정 — 중요도 스코어링
        source_tops = []
        for source, src_items in by_source.items():
            best = max(src_items, key=lambda x: (
                len(x.get("news_articles", [])) * 3,  # 뉴스 인용 수 가중
                len(x.get("summary", "")) if x.get("summary") and not x["summary"].startswith("[") else 0,  # 요약 길이
                1 if x.get("summary") and not x["summary"].startswith("[") else 0,
            ))
            source_tops.append((source, best, len(src_items)))

        # 필수 부처 우선 배치
        must = []
        others = []
        for item in source_tops:
            if item[0] in PRIORITY_SOURCES:
                must.append(item)
            else:
                others.append(item)

        # 나머지는 건수 많은 순
        others.sort(key=lambda x: -x[2])

        # 필수 먼저 + 나머지로 채우기
        result = must + others
        selected[cat] = result[:max_per_cat]

    return selected


def format_daily_message(items: list[dict], target: date, session: str = "") -> str:
    """텔레그램 메시지 포맷 (HTML 모드 — 괄호/특수문자 안전)
    session: 'am' (오전), 'pm' (오후), '' (자동 판단)
    """
    from collections import Counter
    from datetime import datetime

    total = len(items)
    sources = Counter(item["source"] for item in items)
    day_name = DAYS_KO[target.weekday()]

    if not session:
        hour = datetime.now().hour
        session = "am" if hour < 15 else "pm"

    session_label = "오전" if session == "am" else "오후"
    session_emoji = "🌅" if session == "am" else "🌆"

    lines = [
        f"📋 <b>브리핑룸 | {target.month}월 {target.day}일 ({day_name}) {session_label} 보도자료</b>",
        f"",
        f"{session_emoji} {session_label} 업데이트 · 총 {total}건 · {len(sources)}개 부처",
        f"",
    ]

    selected = select_top_articles(items)
    cat_counts = defaultdict(int)
    for item in items:
        cat = CAT_MAP.get(item.get("source", ""), "행정법제")
        cat_counts[cat] += 1

    for cat, emoji in CAT_ORDER:
        if cat not in selected:
            continue
        count = cat_counts.get(cat, 0)
        cat_name = {"금융경제": "금융·경제", "사회복지": "사회·복지", "산업기술": "산업·기술",
                     "외교안보": "외교·안보", "행정법제": "행정·법제"}.get(cat, cat)

        lines.append(f"━━━ {emoji} {cat_name} ({count}건) ━━━")
        lines.append("")

        for source, item, src_count in selected[cat]:
            title = _escape_html(item.get("title", ""))[:55]
            link = _append_query(
                _article_url(item, items),
                ref="telegram",
                session=session or "auto",
                cat=cat,
            )

            lines.append(f"🏛 <b>{_escape_html(source)}</b> ({src_count}건)")
            lines.append(f'▸ <a href="{link}">{title}</a>')

            news = item.get("news_articles", [])
            if news:
                from briefingroom.news import MAJOR_NAMES
                major_news = [a for a in news if a.get("source", "") in MAJOR_NAMES]
                if not major_news:
                    major_news = news[:1]
                for article in major_news[:2]:
                    news_title = _escape_html(article.get("title", ""))[:45]
                    news_src = _escape_html(article.get("source", ""))
                    news_url = (article.get("link", "") or article.get("url", "")).strip()
                    if news_url and not news_url.startswith("http"):
                        news_url = ""
                    if news_url:
                        news_url = news_url.replace("&", "&amp;").replace('"', "%22")
                        lines.append(f'  📰 {news_src}: <a href="{news_url}">{news_title}</a>')
                    else:
                        lines.append(f"  📰 {news_src}: {news_title}")

            # 관련 법령
            related_laws = item.get("related_laws", [])
            if related_laws:
                law_parts = []
                for law in related_laws[:2]:
                    name = _escape_html(law.get("law_name", ""))
                    ref = law.get("article_ref", "")
                    law_parts.append(f"{name} {ref}".strip())
                lines.append(f"  📜 {', '.join(law_parts)}")

            lines.append("")

    lines.append("──────────────────")
    lines.append(f'🔗 <a href="{SITE_URL}">전체 보도자료 보기</a>')

    text = "\n".join(lines)
    if len(text) > 4000:
        # 태그 안전하게 자르기: 마지막 완전한 줄에서 자르기
        cut = text.rfind("\n", 0, 3900)
        if cut > 0:
            text = text[:cut]
        else:
            text = text[:3900]
        text += f'\n\n... <a href="{SITE_URL}">더보기</a>'

    return text


def send_telegram(text: str, bot_token: str = "", chat_id: str = "") -> bool:
    """텔레그램 메시지 발송 — 발송 전 자동 검증"""
    token = bot_token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID

    # 발송 전 검증 + 자동 복구
    errors = _validate_message(text)
    if errors:
        print(f"  ⚠️ 메시지 검증 경고 → 자동 복구 시도:")
        for err in errors:
            print(f"    - {err}")
        text = _fix_html(text)
        errors_after = _validate_message(text)
        if errors_after:
            print(f"  ⚠️ 복구 후에도 {len(errors_after)}건 남음")
        else:
            print(f"  ✅ 자동 복구 성공")

    if not TELEGRAM_ENABLED:
        print("  [텔레그램] TELEGRAM_ENABLED=false → 스킵")
        return False
    if not token or not cid:
        print("  [텔레그램] BOT_TOKEN 또는 CHAT_ID 미설정 → 스킵")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = _split_telegram_html(text)
    for idx, chunk in enumerate(chunks):
        payload = {
            "chat_id": cid,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if idx == 0:
            payload["reply_markup"] = {
                "inline_keyboard": [
                    [
                        {"text": "📋 전체 보기", "url": SITE_URL},
                    ],
                    [
                        {"text": "💰 금융·경제", "url": f"{SITE_URL}/?cat=금융경제"},
                        {"text": "🏥 사회·복지", "url": f"{SITE_URL}/?cat=사회복지"},
                    ],
                    [
                        {"text": "⚙️ 산업·기술", "url": f"{SITE_URL}/?cat=산업기술"},
                        {"text": "🌏 외교·안보", "url": f"{SITE_URL}/?cat=외교안보"},
                    ],
                    [
                        {"text": "📜 행정·법제", "url": f"{SITE_URL}/?cat=행정법제"},
                    ],
                ]
            }

        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200 and r.json().get("ok"):
                msg_id = r.json().get("result", {}).get("message_id")
                print(f"  ✅ 텔레그램 발송 완료 ({idx + 1}/{len(chunks)}, message_id: {msg_id})")
                continue
            print(f"  ❌ 텔레그램 발송 실패: {r.status_code} {r.text[:100]}")
            return False
        except Exception as e:
            print(f"  ❌ 텔레그램 오류: {e}")
            return False
    return True


def format_category_detail(items: list[dict], cat: str, target: date, max_items: int = 8) -> str:
    """분야별 상세 메시지 — 부처 다양하게 최대 8건"""
    cat_name = {"금융경제": "금융·경제", "사회복지": "사회·복지", "산업기술": "산업·기술",
                 "외교안보": "외교·안보", "행정법제": "행정·법제"}.get(cat, cat)
    emoji = dict(CAT_ORDER).get(cat, "📋")
    day_name = DAYS_KO[target.weekday()]

    # 해당 분야 아이템만
    cat_items = [it for it in items if CAT_MAP.get(it.get("source", ""), "행정법제") == cat]
    if not cat_items:
        return ""

    # 부처별 라운드로빈 (다양한 부처에서 골고루)
    by_source = defaultdict(list)
    for it in cat_items:
        by_source[it["source"]].append(it)

    selected = []
    sources = list(by_source.keys())
    # 필수 부처 먼저
    for ps in PRIORITY_SOURCES:
        if ps in sources:
            sources.remove(ps)
            sources.insert(0, ps)

    idx = 0
    while len(selected) < max_items and any(by_source.values()):
        src = sources[idx % len(sources)]
        if by_source[src]:
            selected.append(by_source[src].pop(0))
        else:
            sources.remove(src)
            if not sources:
                break
        idx += 1

    lines = [
        f"{emoji} <b>{cat_name} 상세 | {target.month}월 {target.day}일 ({day_name})</b>",
        f"",
        f"총 {len(cat_items)}건 중 주요 {len(selected)}건",
        f"",
    ]

    for it in selected:
        title = _escape_html(it.get("title", ""))[:55]
        link = _append_query(_article_url(it, items), ref="telegram", detail="category", cat=cat)
        lines.append(f"🏛 <b>{_escape_html(it['source'])}</b>")
        lines.append(f'▸ <a href="{link}">{title}</a>')
        lines.append("")

    lines.append(f'🔗 <a href="{SITE_URL}/?cat={cat}">전체 {cat_name} 보기</a>')
    return "\n".join(lines)


def send_category_details(items: list[dict], target: date) -> int:
    """분야별 상세 메시지 발송 (총합 메시지 뒤에)"""
    sent = 0
    import time as _time
    for cat, emoji in CAT_ORDER:
        text = format_category_detail(items, cat, target)
        if text:
            if send_telegram(text):
                sent += 1
            _time.sleep(1)  # 텔레그램 rate limit 방지
    return sent


def _validate_message(text: str) -> list[str]:
    """발송 전 메시지 검증 — 깨진 링크/태그 탐지"""
    import re as _re
    errors = []

    # HTML 태그 쌍 검증
    for tag in ["b", "a", "i"]:
        opens = len(_re.findall(f"<{tag}[ >]", text))
        closes = len(_re.findall(f"</{tag}>", text))
        if opens != closes:
            errors.append(f"<{tag}> 태그 불일치: open={opens} close={closes}")

    # <a href="..."> 링크 검증
    links = _re.findall(r'<a href="([^"]*)">', text)
    for link in links:
        if not link or not link.startswith("http"):
            errors.append(f"잘못된 링크: {link[:50]}")

    # 이스케이프 안 된 HTML 특수문자
    stripped = _re.sub(r'<[^>]+>', '', text)
    if '<' in stripped or '>' in stripped:
        errors.append("태그 밖에 이스케이프 안 된 <> 문자 존재")

    # 길이 체크
    if len(text) > 4096:
        errors.append(f"메시지 길이 초과: {len(text)}자 > 4096자")

    return errors


def _fix_html(text: str) -> str:
    """깨진 HTML 태그 자동 복구"""
    import re as _re

    # 1. 잘못된 <a> 태그 (닫히지 않은) 제거
    # 닫는 태그 없는 <a>를 찾아 텍스트로 교체
    for tag in ["a", "b", "i"]:
        opens = len(_re.findall(f"<{tag}[ >]", text))
        closes = len(_re.findall(f"</{tag}>", text))
        if opens > closes:
            # 마지막 열린 태그부터 역순으로 닫기
            for _ in range(opens - closes):
                # 가장 마지막 <a href="...">텍스트 를 찾아 태그 제거
                m = list(_re.finditer(f'<{tag}[^>]*>([^<]*?)$', text))
                if m:
                    last = m[-1]
                    text = text[:last.start()] + last.group(1) + text[last.end():]
                else:
                    text += f"</{tag}>"
        elif closes > opens:
            # 여분의 닫는 태그 제거
            for _ in range(closes - opens):
                idx = text.rfind(f"</{tag}>")
                if idx >= 0:
                    text = text[:idx] + text[idx + len(f"</{tag}>"):]

    # 2. 태그 밖 < > 이스케이프
    def _escape_outside_tags(t):
        parts = _re.split(r'(<[^>]+>)', t)
        for i, p in enumerate(parts):
            if not p.startswith('<'):
                parts[i] = p.replace('<', '&lt;').replace('>', '&gt;')
        return ''.join(parts)

    text = _escape_outside_tags(text)

    return text


def _enrich_news(selected: dict) -> None:
    """선정된 보도자료에 Google News 기사를 실시간 검색하여 추가"""
    from briefingroom.news import search_related_news
    import time as _time

    total = 0
    for cat, top_items in selected.items():
        for source, item, src_count in top_items:
            if item.get("news_articles"):
                continue
            articles = search_related_news(item.get("title", ""), source, max_results=5)
            item["news_articles"] = articles[:2]
            total += len(articles[:2])
            _time.sleep(0.3)

    print(f"  뉴스 검색 완료: {total}건 매칭")


def send_daily_briefing(items: list[dict], target: date, session: str = "") -> bool:
    """일일 브리핑 텔레그램 발송 (메인 함수)
    session: 'am' (오전), 'pm' (오후), '' (자동)
    """
    if not items:
        print("  [텔레그램] 보도자료 없음 → 스킵")
        return False

    print(f"\n{'─' * 60}")
    label = {"am": "오전", "pm": "오후"}.get(session, "")
    print(f"[텔레그램 {label} 브리핑 발송]")

    # 선정된 보도자료에 뉴스 기사 실시간 검색
    selected = select_top_articles(items)
    print("  [뉴스 기사 실시간 검색]")
    _enrich_news(selected)

    text = format_daily_message(items, target, session=session)
    print(f"  총합 메시지 길이: {len(text)}자")

    result = send_telegram(text)

    return result


def _clean_text(text: str) -> str:
    """HTML 엔티티 디코딩 + 제목 중복 제거"""
    import html as _html
    text = _html.unescape(text)
    # 제목 반복 제거 (예: "제목제목" → "제목")
    half = len(text) // 2
    if half > 15 and text[:half].strip() == text[half:half * 2].strip():
        text = text[:half].strip()
    return text


def _cut_sentence(text: str, max_len: int = 200) -> str:
    """문장 단위로 잘라서 반환 (마침표/다 기준)"""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    # 마지막 마침표/다 위치 찾기
    for end_char in ["다.", "다.\"", "다.'", "다)", "다, "]:
        idx = cut.rfind(end_char)
        if idx > max_len * 0.4:
            return cut[:idx + len(end_char)]
    # 못 찾으면 마지막 마침표
    idx = cut.rfind(".")
    if idx > max_len * 0.4:
        return cut[:idx + 1]
    return cut + "..."


def format_weekly_main(analysis: dict, selected: dict, target: date) -> str:
    """주간 메인 브리핑 메시지 (A)"""
    start = analysis["start"]
    end = analysis["end"]
    total = analysis["total"]
    prev_total = analysis["prev_total"]

    # 증감 표시
    if prev_total > 0:
        delta_pct = ((total - prev_total) / prev_total) * 100
        delta_str = f"▲{delta_pct:.0f}%" if delta_pct > 0 else (f"▼{abs(delta_pct):.0f}%" if delta_pct < 0 else "━")
    else:
        delta_str = "신규"

    # 키워드 TOP 5
    top_kw = [kw for kw, _ in analysis["keywords"].most_common(5)]
    kw_str = " ".join(f"#{kw}" for kw in top_kw) if top_kw else ""

    lines = [
        f"📊 <b>브리핑룸 | {start.month}/{start.day}~{end.month}/{end.day} 주간 리포트</b>",
        "",
        f"🔢 이번 주 한눈에",
        f"  총 {total}건 · {analysis['sources_count']}개 부처 · 5개 분야",
        f"  전주 대비: {delta_str} ({prev_total}건→{total}건)",
        "",
    ]

    if kw_str:
        lines.append(f"🔥 핵심 키워드")
        lines.append(f"  {kw_str}")
        lines.append("")

    lines.append("━━━ 분야별 TOP 1 ━━━")
    lines.append("")

    for cat, emoji in CAT_ORDER:
        if cat not in selected:
            continue
        src, item, cnt, news_cnt, news_articles = selected[cat]
        cat_total = analysis["by_cat"].get(cat, 0)
        cat_name = {"금융경제": "금융·경제", "사회복지": "사회·복지", "산업기술": "산업·기술",
                     "외교안보": "외교·안보", "행정법제": "행정·법제"}.get(cat, cat)

        title = _escape_html(_clean_text(item.get("title", "")))[:70]
        summary = _clean_text(item.get("summary", ""))
        if summary.startswith("요약:"):
            summary = summary.replace("요약:", "").strip()
        summary = _escape_html(_cut_sentence(summary.split("키워드:")[0].strip()))

        link = _append_query(
            _article_url(item),
            ref="telegram",
            detail="weekly",
            cat=cat,
        )

        lines.append(f"{emoji} <b>{cat_name}</b> ({cat_total}건)")
        lines.append(f"  {_escape_html(src)} | 📰 뉴스 {news_cnt}건")
        lines.append(f'  ▸ <a href="{link}">{title}</a>')
        if summary:
            lines.append(f"  📌 <i>{summary}</i>")
        lines.append("")

    lines.append("──────────────────")
    lines.append(f'🔗 <a href="{SITE_URL}">전체 보도자료 보기</a>')

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3950] + f'\n\n... <a href="{SITE_URL}">더보기</a>'
    return text


def format_weekly_ranking(analysis: dict) -> str:
    """부처 활동 랭킹 메시지 (B)"""
    start = analysis["start"]
    end = analysis["end"]

    lines = [
        f"🏛 <b>이번 주 부처 활동 TOP 10</b>",
        f"  ({start.month}/{start.day}~{end.month}/{end.day})",
        "",
    ]

    top10 = analysis["by_source"].most_common(10)
    for rank, (src, cnt) in enumerate(top10, 1):
        delta = analysis["source_delta"].get(src, 0)
        if delta > 0:
            arrow = f"▲{delta}"
        elif delta < 0:
            arrow = f"▼{abs(delta)}"
        else:
            arrow = "━"
        lines.append(f"  {rank:>2}. {_escape_html(src):<14} {cnt}건 {arrow}")

    lines.append("")

    # 급등/급락
    rises = sorted(analysis["source_delta"].items(), key=lambda x: -x[1])[:3]
    falls = sorted(analysis["source_delta"].items(), key=lambda x: x[1])[:3]

    notable_rises = [(s, d) for s, d in rises if d > 3]
    notable_falls = [(s, d) for s, d in falls if d < -3]

    if notable_rises:
        rise_str = ", ".join(f"{s}(+{d})" for s, d in notable_rises)
        lines.append(f"📈 급등: {_escape_html(rise_str)}")
    if notable_falls:
        fall_str = ", ".join(f"{s}({d})" for s, d in notable_falls)
        lines.append(f"📉 급락: {_escape_html(fall_str)}")

    # 신규 부처 (전주 0건 → 이번 주 등장)
    new_sources = [(s, c) for s, c in analysis["by_source"].items()
                   if analysis["prev_by_source"].get(s, 0) == 0 and c > 0]
    if new_sources:
        new_str = ", ".join(f"{s}({c}건)" for s, c in sorted(new_sources, key=lambda x: -x[1])[:3])
        lines.append(f"🆕 이번 주 신규: {_escape_html(new_str)}")

    return "\n".join(lines)


def format_weekly_keywords(analysis: dict) -> str:
    """키워드 트렌드 메시지 (C)"""
    start = analysis["start"]
    end = analysis["end"]

    lines = [
        f"🔍 <b>이번 주 정책 키워드 트렌드</b>",
        f"  ({start.month}/{start.day}~{end.month}/{end.day})",
        "",
    ]

    # 급상승 (신규 또는 +50% 이상)
    rising = [(kw, d) for kw, d in analysis["kw_delta"].items()
              if d["change_pct"] >= 50 and d["count"] >= 3]
    rising.sort(key=lambda x: -x[1]["change_pct"])

    if rising:
        lines.append("📈 급상승")
        for kw, d in rising[:5]:
            if d["prev"] == 0:
                pct = "신규"
            else:
                pct = f"+{d['change_pct']:.0f}%"
            lines.append(f"  #{_escape_html(kw)} ({d['count']}회, {pct})")
        lines.append("")

    # 꾸준한 관심 (전주와 비슷, 3회 이상)
    steady = [(kw, d) for kw, d in analysis["kw_delta"].items()
              if -30 < d["change_pct"] < 50 and d["count"] >= 3 and d["prev"] > 0]
    steady.sort(key=lambda x: -x[1]["count"])

    if steady:
        lines.append("📊 꾸준한 관심")
        for kw, d in steady[:5]:
            lines.append(f"  #{_escape_html(kw)} ({d['count']}회)")
        lines.append("")

    # 키워드-부처 연결 (TOP 3 키워드에 대해)
    if analysis["keywords"]:
        lines.append("🔗 키워드 연결")
        # DB에서 키워드-부처 매핑은 items_by_cat에서 추출
        all_items = []
        for cat_items in analysis["items_by_cat"].values():
            all_items.extend(cat_items)

        for kw, _ in analysis["keywords"].most_common(3):
            sources = Counter()
            for it in all_items:
                if it.get("keywords") and kw in it["keywords"]:
                    sources[it["source"]] += 1
            if sources:
                src_str = ", ".join(f"{s}({c})" for s, c in sources.most_common(3))
                lines.append(f"  #{_escape_html(kw)} ← {_escape_html(src_str)}")

    return "\n".join(lines)


def send_weekly_briefing(target: date) -> bool:
    """주간 브리핑 3건 연속 발송 (메인 함수)"""
    import time as _time

    print(f"\n{'═' * 60}")
    print(f"[주간 브리핑 발송]")

    # 1. 주간 분석
    print("  [1/4] 주간 데이터 분석 중...")
    analysis = analyze_weekly(target)
    if analysis["total"] == 0:
        print("  주간 데이터 없음 → 스킵")
        return False
    print(f"  이번 주: {analysis['total']}건 / 전주: {analysis['prev_total']}건")

    # 2. 분야별 TOP 1 선정 (Google News RSS 검색)
    print("  [2/4] 분야별 TOP 1 선정 (뉴스 검색 중)...")
    selected = select_weekly_top(analysis)
    print(f"  선정 완료: {len(selected)}개 분야")

    # 3. 메시지 포맷
    print("  [3/4] 메시지 생성 중...")
    msg_main = format_weekly_main(analysis, selected, target)
    msg_ranking = format_weekly_ranking(analysis)
    msg_keywords = format_weekly_keywords(analysis)

    print(f"  메인: {len(msg_main)}자 / 랭킹: {len(msg_ranking)}자 / 키워드: {len(msg_keywords)}자")

    # 4. 발송
    print("  [4/4] 텔레그램 발송...")
    ok = True
    for label, text in [("메인", msg_main), ("키워드", msg_keywords)]:
        result = send_telegram(text)
        if not result:
            ok = False
            print(f"  ❌ {label} 발송 실패")
        _time.sleep(1)

    return ok
