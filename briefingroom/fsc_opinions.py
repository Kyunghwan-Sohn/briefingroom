"""금융위원회 비조치의견서 + 과거회신사례 크롤러

better.fsc.go.kr에서 비조치의견서(1,669건)와 과거회신사례(4,256건)를
수집하여 finance_law.db에 저장합니다.

카테고리: 비조치의견서, 법령해석, 행정지도, 감독행정
분야: 공통, 자본시장, 보험, 은행, 저축은행, 여전, 신용정보 등

실행: python -m briefingroom.fsc_opinions
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from briefingroom.config import BASE_DIR, DATA_DIR, PROXIES
from briefingroom.http import build_session

DB_PATH = BASE_DIR / "finance_law.db"
BASE_URL = "https://better.fsc.go.kr/fsc_new/replyCase"
DETAIL_URL = "https://better.fsc.go.kr/fsc_new/replyCase/OpinionView.do"
BATCH_SIZE = 100
DETAIL_BACKFILL_LIMIT = int(os.environ.get("FSC_DETAIL_BACKFILL_LIMIT", "50"))
DETAIL_SLEEP = float(os.environ.get("FSC_DETAIL_SLEEP", "0.2"))
_session = None


def _get_session():
    global _session
    if _session is None:
        _session = build_session(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; govbrief/1.0)",
                "X-Requested-With": "XMLHttpRequest",
            },
            retries=2,
        )
        if PROXIES:
            _session.proxies.update(PROXIES)
    return _session


def _init_tables(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fsc_opinions (
            opinion_id INTEGER PRIMARY KEY,
            opinion_number TEXT,
            gubun TEXT,
            category TEXT,
            title TEXT NOT NULL,
            status TEXT,
            reg_date TEXT,
            content TEXT,
            reply TEXT,
            related_law TEXT,
            detail_link TEXT,
            crawled_at TEXT
        )
    """)
    conn.commit()


def _fetch_list(endpoint: str, page: int = 0, size: int = BATCH_SIZE) -> dict:
    """DataTables API 호출"""
    r = _get_session().post(
        f"{BASE_URL}/{endpoint}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "draw": str(page + 1),
            "start": str(page * size),
            "length": str(size),
        },
        timeout=15,
    )
    if r.status_code != 200:
        return {"data": [], "recordsTotal": 0}
    return r.json()


def _fetch_detail(opinion_id: int) -> dict:
    """비조치의견서 상세 조회"""
    try:
        r = _get_session().get(
            f"{DETAIL_URL}?opinionIdx={opinion_id}",
            timeout=15,
        )
        if r.status_code != 200:
            return {}

        soup = BeautifulSoup(r.text, "lxml")

        def clean_text(value: str) -> str:
            text = re.sub(r"\s+", " ", value or "").strip()
            return text[:4000]

        def by_label(labels: tuple[str, ...]) -> str:
            patterns = tuple(label.replace(" ", "") for label in labels)
            for node in soup.select("th, dt, strong, b, .title, .tit"):
                label = node.get_text(" ", strip=True).replace(" ", "")
                if not label or not any(key in label for key in patterns):
                    continue
                sibling = node.find_next(["td", "dd", "div", "p"])
                if sibling:
                    text = clean_text(sibling.get_text(" ", strip=True))
                    if text and text != label:
                        return text
            return ""

        def by_class(patterns: tuple[str, ...]) -> str:
            for pattern in patterns:
                node = soup.select_one(pattern)
                if node:
                    text = clean_text(node.get_text(" ", strip=True))
                    if text:
                        return text
            return ""

        content = by_label(("질의내용", "질의", "신청내용"))
        reply = by_label(("회신내용", "회답내용", "검토의견", "답변"))

        if not content:
            content = by_class((
                ".question", ".content", ".board_cont", ".board-view .cont",
                ".view_cont", ".detail_cont", ".tbl-view td",
            ))
        if not reply:
            reply = by_class((
                ".reply", ".answer", ".result", ".response",
                ".board_cont.answer", ".board_cont.reply",
            ))

        return {"content": content[:2000], "reply": reply[:2000]}
    except Exception:
        return {}


def backfill_missing_details(limit: int = DETAIL_BACKFILL_LIMIT) -> int:
    """본문이 비어 있는 비조치의견서 상세를 점진적으로 보강"""
    if limit <= 0:
        return 0

    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    rows = conn.execute(
        "SELECT opinion_id FROM fsc_opinions "
        "WHERE detail_link != '' "
        "AND (COALESCE(content, '') = '' OR COALESCE(reply, '') = '') "
        "ORDER BY reg_date DESC, opinion_id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    updated = 0

    for (opinion_id,) in rows:
        detail = _fetch_detail(opinion_id)
        content = detail.get("content", "")
        reply = detail.get("reply", "")
        if not content and not reply:
            continue
        conn.execute(
            "UPDATE fsc_opinions SET content = ?, reply = ?, crawled_at = ? WHERE opinion_id = ?",
            (content, reply, datetime.now().isoformat(), opinion_id),
        )
        updated += 1
        time.sleep(DETAIL_SLEEP)

    conn.commit()
    conn.close()
    print(f"[fsc_opinions] 본문 보강 {updated}/{len(rows)}건")
    return updated


def generate_opinion_stats() -> dict:
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    total = conn.execute("SELECT COUNT(*) FROM fsc_opinions").fetchone()[0]
    content_count = conn.execute(
        "SELECT COUNT(*) FROM fsc_opinions WHERE COALESCE(content, '') != ''"
    ).fetchone()[0]
    reply_count = conn.execute(
        "SELECT COUNT(*) FROM fsc_opinions WHERE COALESCE(reply, '') != ''"
    ).fetchone()[0]
    by_gubun = conn.execute(
        "SELECT gubun, COUNT(*) FROM fsc_opinions GROUP BY gubun ORDER BY COUNT(*) DESC"
    ).fetchall()
    by_cat = conn.execute(
        "SELECT category, COUNT(*) FROM fsc_opinions GROUP BY category ORDER BY COUNT(*) DESC"
    ).fetchall()
    conn.close()

    stats = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": total,
        "content_count": content_count,
        "reply_count": reply_count,
        "content_pct": round((content_count / total) * 100, 1) if total else 0,
        "reply_pct": round((reply_count / total) * 100, 1) if total else 0,
        "by_gubun": [{"name": g or "기타", "count": c} for g, c in by_gubun],
        "by_category": [{"name": cat or "기타", "count": c} for cat, c in by_cat[:20]],
    }

    out_path = DATA_DIR / "opinions-stats.json"
    out_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fsc_opinions] opinions-stats.json 생성 — 전체 {total}건, 본문 {content_count}건")
    return stats


def crawl_opinions(fetch_details: bool = False) -> int:
    """비조치의견서 목록 전체 크롤링"""
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    _init_tables(conn)

    total_saved = 0
    page = 0

    while True:
        data = _fetch_list("selectReplyCaseOpinionList.do", page, BATCH_SIZE)
        items = data.get("data", [])
        total = data.get("recordsTotal", 0)

        if not items:
            break

        now = datetime.now().isoformat()
        for item in items:
            opinion_id = item.get("opinionIdx", 0)
            if not opinion_id:
                continue

            # 상세 조회 (선택적)
            content = ""
            reply = ""
            if fetch_details:
                detail = _fetch_detail(opinion_id)
                content = detail.get("content", "")
                reply = detail.get("reply", "")
                time.sleep(0.3)

            conn.execute("""
                INSERT OR REPLACE INTO fsc_opinions
                (opinion_id, opinion_number, gubun, category, title, status,
                 reg_date, content, reply, related_law, detail_link, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opinion_id,
                item.get("opinionNumber", ""),
                "비조치의견서",
                item.get("category", ""),
                item.get("title", ""),
                item.get("status", ""),
                item.get("regDate", ""),
                content,
                reply,
                "",
                f"https://better.fsc.go.kr/fsc_new/replyCase/OpinionView.do?opinionIdx={opinion_id}",
                now,
            ))
            total_saved += 1

        conn.commit()
        print(f"  [비조치의견서] 페이지 {page+1} — {len(items)}건 (누적 {total_saved}/{total})")
        page += 1

        if page * BATCH_SIZE >= total:
            break
        time.sleep(0.5)

    conn.close()
    return total_saved


def crawl_past_replies() -> int:
    """과거회신사례 전체 크롤링 (비조치의견서 + 법령해석 + 행정지도 등)"""
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    _init_tables(conn)

    total_saved = 0
    page = 0

    while True:
        data = _fetch_list("selectReplyCasePastReplyList.do", page, BATCH_SIZE)
        items = data.get("data", [])
        total = data.get("recordsTotal", 0)

        if not items:
            break

        now = datetime.now().isoformat()
        for item in items:
            idx = item.get("idx", 0)
            if not idx:
                continue

            conn.execute("""
                INSERT OR IGNORE INTO fsc_opinions
                (opinion_id, opinion_number, gubun, category, title, status,
                 reg_date, content, reply, related_law, detail_link, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                idx,
                item.get("opinionNumber", ""),
                item.get("gubun", ""),
                item.get("category", ""),
                item.get("title", ""),
                item.get("status", "완료"),
                item.get("regDate", ""),
                "",
                "",
                "",
                f"https://better.fsc.go.kr/fsc_new/replyCase/OpinionView.do?opinionIdx={idx}",
                now,
            ))
            total_saved += 1

        conn.commit()
        print(f"  [과거회신] 페이지 {page+1} — {len(items)}건 (누적 {total_saved}/{total})")
        page += 1

        if page * BATCH_SIZE >= total:
            break
        time.sleep(0.5)

    conn.close()
    return total_saved


def main():
    print("=" * 50)
    print("금융위원회 비조치의견서 + 과거회신사례 크롤링")
    print("=" * 50)

    fetch_details = os.environ.get("FSC_FETCH_DETAILS", "").lower() in ("1", "true", "yes")
    skip_past_replies = os.environ.get("FSC_SKIP_PAST_REPLIES", "").lower() in ("1", "true", "yes")

    n1 = crawl_opinions(fetch_details=fetch_details)
    print(f"\n비조치의견서: {n1}건 저장")

    n2 = 0
    if not skip_past_replies:
        n2 = crawl_past_replies()
    print(f"과거회신사례: {n2}건 저장")

    backfill_missing_details()
    generate_opinion_stats()

    # 최종 통계
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    total = conn.execute("SELECT COUNT(*) FROM fsc_opinions").fetchone()[0]
    by_gubun = conn.execute("SELECT gubun, COUNT(*) FROM fsc_opinions GROUP BY gubun").fetchall()
    by_cat = conn.execute("SELECT category, COUNT(*) FROM fsc_opinions GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
    conn.close()

    print(f"\n{'='*50}")
    print(f"전체: {total}건")
    print("유형별:")
    for g, c in by_gubun:
        print(f"  {g}: {c}건")
    print("분야별:")
    for cat, c in by_cat[:10]:
        print(f"  {cat}: {c}건")


if __name__ == "__main__":
    main()
