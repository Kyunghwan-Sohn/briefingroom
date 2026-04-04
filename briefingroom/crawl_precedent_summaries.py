"""판례 요약 크롤링 스크립트

법제처 웹에서 판결요지를 수집하여 finance_law.db에 저장합니다.

실행: python -m briefingroom.crawl_precedent_summaries
"""
from __future__ import annotations
import sqlite3
import time
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"
sess = requests.Session()
sess.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; govbrief.kr/1.0)"})


def fetch_summary(prec_id: str) -> str:
    """법제처 웹에서 판결요지 추출"""
    try:
        url = f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={prec_id}"
        r = sess.get(url, timeout=20)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        # 【판결요지】 또는 【판시사항】 찾기
        for h in soup.find_all(["h4", "h3", "dt"]):
            t = h.get_text(strip=True)
            if "판결요지" in t or "판시사항" in t:
                sib = h.find_next_sibling()
                if sib:
                    text = sib.get_text(separator="\n", strip=True)
                    if len(text) > 20:
                        return text[:3000]
        # bodyContent에서 직접 추출
        body = soup.find("div", id="contentBody") or soup.find("div", id="bodyContent")
        if body:
            text = body.get_text(separator="\n", strip=True)
            # 【판결요지】 이후 텍스트 추출
            m = re.search(r"【판결요지】\s*(.*?)(?:【|$)", text, re.DOTALL)
            if m and len(m.group(1).strip()) > 20:
                return m.group(1).strip()[:3000]
            m = re.search(r"【판시사항】\s*(.*?)(?:【|$)", text, re.DOTALL)
            if m and len(m.group(1).strip()) > 20:
                return m.group(1).strip()[:3000]
            # 전체 본문 앞 1000자
            if len(text) > 100:
                return text[:1500]
    except Exception as e:
        print(f"  [ERR] {prec_id}: {e}")
    return ""


def run():
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT prec_id, case_name FROM precedents "
        "WHERE (summary IS NULL OR summary = '' OR summary = '-' OR length(summary) < 20) "
        "ORDER BY decision_date DESC"
    ).fetchall()
    print(f"[crawl_prec] 요약 없는 판례 {len(rows)}건 처리 시작")

    updated = 0
    for i, (prec_id, name) in enumerate(rows):
        print(f"  [{i+1}/{len(rows)}] {name[:40]}...")
        summary = fetch_summary(prec_id)
        if summary and len(summary) > 20:
            conn.execute(
                "UPDATE precedents SET summary = ? WHERE prec_id = ?",
                (summary, prec_id)
            )
            conn.commit()
            updated += 1
            print(f"    [OK] {len(summary)}자")
        else:
            print(f"    [SKIP] 요약 없음")
        time.sleep(1)

    conn.close()
    print(f"\n[crawl_prec] 완료: {updated}/{len(rows)}건 업데이트")


if __name__ == "__main__":
    run()
