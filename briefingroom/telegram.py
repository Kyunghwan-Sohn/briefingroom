"""텔레그램 일일 브리핑 발송

오후 6시 당일 보도자료 종합 → 분야별 대표 1~2건 → 텔레그램 채널 발송
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from datetime import date

import requests

from briefingroom.config import CAT_MAP, FINANCE_SUB_MAP

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SITE_URL = "https://hotclipfolio.com"

# 분야 순서 + 이모지
CAT_ORDER = [
    ("금융경제", "💰"),
    ("사회복지", "🏥"),
    ("산업기술", "⚙️"),
    ("외교안보", "🌏"),
    ("행정법제", "📜"),
]

DAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]


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

        # 부처별 대표 1건 선정
        source_tops = []
        for source, src_items in by_source.items():
            best = max(src_items, key=lambda x: (
                len(x.get("news_articles", [])),
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
    """텔레그램 메시지 포맷 (Markdown)
    session: 'am' (오전), 'pm' (오후), '' (자동 판단)
    """
    from collections import Counter
    from datetime import datetime

    total = len(items)
    sources = Counter(item["source"] for item in items)
    day_name = DAYS_KO[target.weekday()]

    # 오전/오후 자동 판단
    if not session:
        hour = datetime.now().hour
        session = "am" if hour < 15 else "pm"

    session_label = "오전" if session == "am" else "오후"
    session_emoji = "🌅" if session == "am" else "🌆"

    # 헤더
    lines = [
        f"📋 *브리핑룸 | {target.month}월 {target.day}일 ({day_name}) {session_label} 보도자료*",
        f"",
        f"{session_emoji} {session_label} 업데이트 · 총 {total}건 · {len(sources)}개 부처",
        f"",
    ]

    # 분야별 섹션
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
            title = item.get("title", "")[:55]
            wp_id = item.get("wp_post_id", "")
            detail_link = f"{SITE_URL}/?p={wp_id}" if wp_id else SITE_URL

            lines.append(f"🏛 *{source}* ({src_count}건)")
            lines.append(f"▸ [{title}]({detail_link})")

            # 관련 뉴스 기사
            news = item.get("news_articles", [])
            if news:
                news_text = " · ".join(a["source"] for a in news[:3])
                lines.append(f"  📰 {news_text}")

            lines.append("")

    # 푸터
    lines.append("──────────────────")
    lines.append(f"🔗 [전체 보도자료 보기]({SITE_URL})")

    text = "\n".join(lines)

    # 텔레그램 4096자 제한
    if len(text) > 4000:
        text = text[:3950] + "\n\n... 더보기: " + SITE_URL

    return text


def send_telegram(text: str, bot_token: str = None, chat_id: str = None) -> bool:
    """텔레그램 메시지 발송"""
    token = bot_token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID

    if not token or not cid:
        print("  [텔레그램] BOT_TOKEN 또는 CHAT_ID 미설정 → 스킵")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": cid,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "reply_markup": {
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
        },
    }

    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200 and r.json().get("ok"):
            msg_id = r.json().get("result", {}).get("message_id")
            print(f"  ✅ 텔레그램 발송 완료 (message_id: {msg_id})")
            return True
        else:
            print(f"  ❌ 텔레그램 발송 실패: {r.status_code} {r.text[:100]}")
            return False
    except Exception as e:
        print(f"  ❌ 텔레그램 오류: {e}")
        return False


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
        f"{emoji} *{cat_name} 상세 | {target.month}월 {target.day}일 ({day_name})*",
        f"",
        f"총 {len(cat_items)}건 중 주요 {len(selected)}건",
        f"",
    ]

    for it in selected:
        title = it.get("title", "")[:55]
        wp_id = it.get("wp_post_id", "")
        link = f"{SITE_URL}/?p={wp_id}" if wp_id else SITE_URL
        lines.append(f"🏛 *{it['source']}*")
        lines.append(f"▸ [{title}]({link})")
        lines.append("")

    lines.append(f"🔗 [전체 {cat_name} 보기]({SITE_URL}/?cat={cat})")
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

    text = format_daily_message(items, target, session=session)
    print(f"  총합 메시지 길이: {len(text)}자")

    result = send_telegram(text)

    # 분야별 상세 메시지 발송
    if result:
        import time as _time
        _time.sleep(2)
        print("  [분야별 상세 발송]")
        sent = send_category_details(items, target)
        print(f"  분야별 {sent}건 발송 완료")

    return result
