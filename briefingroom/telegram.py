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


def select_top_articles(items: list[dict], max_per_cat: int = 2, max_per_source: int = 1) -> dict:
    """분야별 대표 보도자료 선정 (뉴스 기사 많은 건 우선)"""
    by_cat = defaultdict(list)
    for item in items:
        cat = CAT_MAP.get(item.get("source", ""), "행정법제")
        by_cat[cat].append(item)

    selected = {}  # cat → [(item, news_count)]
    for cat, cat_items in by_cat.items():
        # 부처별 그룹핑
        by_source = defaultdict(list)
        for item in cat_items:
            by_source[item["source"]].append(item)

        # 부처별 대표 1건 선정 (뉴스 기사 수 > LLM 요약 유무 > 최근)
        source_tops = []
        for source, src_items in by_source.items():
            best = max(src_items, key=lambda x: (
                len(x.get("news_articles", [])),
                1 if x.get("summary") and not x["summary"].startswith("[") else 0,
            ))
            source_tops.append((source, best, len(src_items)))

        # 건수 많은 부처 우선
        source_tops.sort(key=lambda x: -x[2])
        selected[cat] = source_tops[:max_per_cat]

    return selected


def format_daily_message(items: list[dict], target: date) -> str:
    """텔레그램 메시지 포맷 (Markdown)"""
    from collections import Counter

    total = len(items)
    sources = Counter(item["source"] for item in items)
    day_name = DAYS_KO[target.weekday()]

    # 헤더
    lines = [
        f"📋 *브리핑룸 | {target.month}월 {target.day}일 ({day_name}) 일일 보도자료*",
        f"",
        f"총 {total}건 수집 · {len(sources)}개 부처",
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
    lines.append(f"📧 [이메일 구독]({SITE_URL}/subscribe)")

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
                    {"text": "📧 이메일 구독", "url": f"{SITE_URL}/subscribe"},
                ],
                [
                    {"text": "💰 금융 특화", "url": f"{SITE_URL}/?filter=finance"},
                    {"text": "📰 오늘의 기사", "url": f"{SITE_URL}/?filter=news"},
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


def send_daily_briefing(items: list[dict], target: date) -> bool:
    """일일 브리핑 텔레그램 발송 (메인 함수)"""
    if not items:
        print("  [텔레그램] 보도자료 없음 → 스킵")
        return False

    print(f"\n{'─' * 60}")
    print("[텔레그램 일일 브리핑 발송]")

    text = format_daily_message(items, target)
    print(f"  메시지 길이: {len(text)}자")

    return send_telegram(text)
