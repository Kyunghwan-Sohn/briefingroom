"""finance_law.db 동기화 스크립트

법제처 Open API를 통해 금융법령 DB의 laws, precedents 테이블을 업데이트합니다.
- laws: amendment_reason (개정이유) 컬럼 추가 및 갱신
- precedents: summary (판결요지) 컬럼 갱신

실행: python -m briefingroom.finlaw_sync
GitHub Actions에서 주 1회 실행 권장 (IP 등록 필요).
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import requests

from briefingroom.config import BASE_DIR, PROXIES

LAW_OC = "sony0125"
API_BASE = "http://www.law.go.kr/DRF"
DB_PATH = BASE_DIR / "finance_law.db"

_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": "govbrief.kr/1.0"})
        if PROXIES:
            _session.proxies.update(PROXIES)
    return _session


def _ensure_columns(conn: sqlite3.Connection):
    """필요한 컬럼이 없으면 추가"""
    cursor = conn.execute("PRAGMA table_info(laws)")
    cols = {r[1] for r in cursor.fetchall()}
    if "amendment_reason" not in cols:
        conn.execute("ALTER TABLE laws ADD COLUMN amendment_reason TEXT DEFAULT ''")
        print("[finlaw_sync] laws.amendment_reason 컬럼 추가")
        conn.commit()


def sync_amendment_reasons(limit: int = 200):
    """laws 테이블에서 amendment_reason이 비어 있는 법령의 개정이유를 가져옵니다."""
    conn = sqlite3.connect(str(DB_PATH))
    _ensure_columns(conn)

    rows = conn.execute(
        "SELECT law_mst, name FROM laws "
        "WHERE (amendment_reason IS NULL OR amendment_reason = '') "
        "AND law_mst != '' "
        "ORDER BY promulgation_date DESC LIMIT ?",
        (limit,),
    ).fetchall()

    print(f"[finlaw_sync] 개정이유 미수집 법령 {len(rows)}건 처리 시작")
    updated = 0
    sess = _get_session()

    for mst, name in rows:
        try:
            r = sess.get(
                f"{API_BASE}/lawService.do",
                params={"OC": LAW_OC, "target": "law", "MST": mst, "type": "JSON"},
                timeout=15,
            )
            if r.status_code != 200:
                print(f"  [SKIP] {name} — HTTP {r.status_code}")
                continue

            data = r.json()
            law_data = data.get("법령", {})
            amend = law_data.get("개정문", {})
            # 개정문내용은 배열의 배열 형태 [[제목, 내용, ...]]
            raw = amend.get("개정문내용", "")
            reason = ""
            if isinstance(raw, list):
                # 첫 번째 배열에서 텍스트 합치기 (제목 제외, 본문만)
                flat = raw[0] if raw and isinstance(raw[0], list) else raw
                texts = [s for s in flat if isinstance(s, str) and len(s) > 20]
                reason = " ".join(texts[:3]) if texts else ""
            elif isinstance(raw, str):
                reason = raw

            if reason:
                # 앞 500자만 저장 (개정이유가 매우 길 수 있음)
                reason = reason.strip()[:500]
                conn.execute(
                    "UPDATE laws SET amendment_reason = ? WHERE law_mst = ?",
                    (reason, mst),
                )
                conn.commit()
                updated += 1
                print(f"  [OK] {name} — {len(reason)}자")
            else:
                # 빈 값이라도 마킹하여 재시도 방지
                conn.execute(
                    "UPDATE laws SET amendment_reason = '-' WHERE law_mst = ?",
                    (mst,),
                )
                conn.commit()
                print(f"  [EMPTY] {name}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  [ERR] {name} — {e}")
            continue

    conn.close()
    print(f"[finlaw_sync] 완료 — {updated}/{len(rows)}건 개정이유 수집")
    return updated


def sync_precedent_summaries(limit: int = 200):
    """precedents 테이블에서 summary가 비어 있는 판례 요지를 가져옵니다."""
    conn = sqlite3.connect(str(DB_PATH))

    rows = conn.execute(
        "SELECT prec_id, case_name FROM precedents "
        "WHERE (summary IS NULL OR summary = '') "
        "ORDER BY decision_date DESC LIMIT ?",
        (limit,),
    ).fetchall()

    print(f"[finlaw_sync] 판례요지 미수집 {len(rows)}건 처리 시작")
    updated = 0
    sess = _get_session()

    for prec_id, case_name in rows:
        try:
            r = sess.get(
                f"{API_BASE}/lawService.do",
                params={"OC": LAW_OC, "target": "prec", "ID": prec_id, "type": "JSON"},
                timeout=15,
            )
            if r.status_code != 200:
                print(f"  [SKIP] {case_name} — HTTP {r.status_code}")
                continue

            data = r.json()
            prec_data = data.get("PrecService", {})
            summary = prec_data.get("판례내용", "")
            if not summary:
                summary = prec_data.get("판시사항", "")
            if not summary:
                summary = prec_data.get("판결요지", "")

            if summary:
                summary = summary.strip()[:500]
                conn.execute(
                    "UPDATE precedents SET summary = ? WHERE prec_id = ?",
                    (summary, prec_id),
                )
                conn.commit()
                updated += 1
                print(f"  [OK] {case_name[:30]} — {len(summary)}자")
            else:
                conn.execute(
                    "UPDATE precedents SET summary = '-' WHERE prec_id = ?",
                    (prec_id,),
                )
                conn.commit()
                print(f"  [EMPTY] {case_name[:30]}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  [ERR] {case_name[:30]} — {e}")
            continue

    conn.close()
    print(f"[finlaw_sync] 완료 — {updated}/{len(rows)}건 판례요지 수집")
    return updated


def main():
    print("=" * 50)
    print("finance_law.db 동기화 시작")
    print("=" * 50)
    sync_amendment_reasons()
    sync_precedent_summaries()
    print("동기화 완료")


if __name__ == "__main__":
    main()
