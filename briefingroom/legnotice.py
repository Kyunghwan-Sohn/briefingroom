"""입법예고 크롤러

opinion.lawmaking.go.kr에서 금융 관련 입법예고를 수집하여
finance_law.db의 leg_notices 테이블에 저장합니다.

실행: python -m briefingroom.legnotice
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

import requests

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"
CRAWL_URL = "https://opinion.lawmaking.go.kr/gcom/ogLmPp"

# 금융 관련 부처/키워드
_FIN_KEYWORDS = [
    "금융", "자본시장", "보험", "은행", "신용", "전자금융",
    "가상자산", "증권", "여신", "예금", "대부업", "핀테크",
]


def _init_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leg_notices (
            notice_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            department TEXT,
            law_type TEXT,
            period_start TEXT,
            period_end TEXT,
            days INTEGER,
            opinion_count INTEGER DEFAULT 0,
            detail_link TEXT,
            crawled_at TEXT
        )
    """)
    conn.commit()


def _parse_date(text: str) -> str:
    """'2026. 4. 1.' → '2026-04-01'"""
    m = re.match(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", text.strip())
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return ""


def _is_financial(title: str, dept: str) -> bool:
    combined = title + " " + dept
    return any(k in combined for k in _FIN_KEYWORDS)


def crawl_leg_notices(pages: int = 3) -> list[dict]:
    """입법예고 크롤링 — 금융 관련만 필터링"""
    results = []
    seen = set()

    for page in range(1, pages + 1):
        try:
            r = requests.get(
                CRAWL_URL,
                params={"pageIndex": str(page), "cntPerPage": "100"},
                headers={"User-Agent": "Mozilla/5.0 (govbrief.kr)"},
                timeout=15,
            )
            if r.status_code != 200:
                print(f"  [입법예고] 페이지 {page} HTTP {r.status_code}")
                continue

            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.DOTALL)
            for row in rows[1:]:  # skip header
                tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
                if len(tds) < 7:
                    continue

                no = re.sub(r"<[^>]+>|\s+", " ", tds[0]).strip()
                title = re.sub(r"<[^>]+>|\s+", " ", tds[1]).strip()
                dept_raw = re.sub(r"<[^>]+>|\s+", " ", tds[2]).strip()
                period = re.sub(r"<[^>]+>|\s+", " ", tds[4]).strip()
                days = re.sub(r"<[^>]+>|\s+", " ", tds[5]).strip()
                opinions = re.sub(r"<[^>]+>|\s+", " ", tds[6]).strip()

                # 부처 + 법종류 분리 (예: "금융위원회 (대통령령)")
                dept_m = re.match(r"(.+?)\s*\((.+?)\)", dept_raw)
                dept = dept_m.group(1) if dept_m else dept_raw
                law_type = dept_m.group(2) if dept_m else ""

                # 금융 관련 필터
                if not _is_financial(title, dept):
                    continue

                if no in seen:
                    continue
                seen.add(no)

                # 기간 파싱
                period_parts = period.split("~")
                p_start = _parse_date(period_parts[0]) if len(period_parts) >= 1 else ""
                p_end = _parse_date(period_parts[1]) if len(period_parts) >= 2 else ""

                # 의견 수
                op_m = re.search(r"(\d+)", opinions)
                op_count = int(op_m.group(1)) if op_m else 0

                # 상세 링크
                link_m = re.search(r'href="([^"]+)"', tds[1])
                detail = link_m.group(1) if link_m else ""
                if detail and not detail.startswith("http"):
                    detail = f"https://opinion.lawmaking.go.kr{detail}"

                # D-day 계산
                days_num = 0
                if p_end:
                    try:
                        end_date = datetime.strptime(p_end, "%Y-%m-%d").date()
                        days_num = (end_date - date.today()).days
                    except ValueError:
                        pass

                results.append({
                    "notice_id": no,
                    "title": title,
                    "department": dept,
                    "law_type": law_type,
                    "period_start": p_start,
                    "period_end": p_end,
                    "days": days_num,
                    "opinion_count": op_count,
                    "detail_link": detail,
                })

            print(f"  [입법예고] 페이지 {page} — {len(rows)-1}건 중 금융 {len(results)}건")

        except Exception as e:
            print(f"  [입법예고] 페이지 {page} 에러: {e}")

    return results


def save_notices(notices: list[dict]):
    """입법예고 DB 저장"""
    conn = sqlite3.connect(str(DB_PATH))
    _init_table(conn)
    now = datetime.now().isoformat()
    saved = 0
    for n in notices:
        conn.execute("""
            INSERT OR REPLACE INTO leg_notices
            (notice_id, title, department, law_type, period_start, period_end,
             days, opinion_count, detail_link, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            n["notice_id"], n["title"], n["department"], n["law_type"],
            n["period_start"], n["period_end"], n["days"],
            n["opinion_count"], n["detail_link"], now,
        ))
        saved += 1
    conn.commit()
    conn.close()
    print(f"[입법예고] {saved}건 저장 완료")
    return saved


def main():
    print("=" * 50)
    print("입법예고 크롤링 시작")
    print("=" * 50)
    notices = crawl_leg_notices(pages=5)
    if notices:
        save_notices(notices)
        for n in notices:
            d_day = f"D-{n['days']}" if n["days"] > 0 else "마감"
            print(f"  [{d_day}] {n['department']} — {n['title'][:50]}")
    else:
        print("금융 관련 입법예고 없음")


if __name__ == "__main__":
    main()
