"""LawDiff 알림 데이터 생성

최근 개정 법령 중 알림 대상으로 볼 만한 항목을 추려
JSON 피드와 발송용 텍스트를 생성합니다.

실행: python -m briefingroom.lawdiff_alerts
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timedelta

from briefingroom.config import BASE_DIR, DATA_DIR

DB_PATH = BASE_DIR / "finance_law.db"
STATE_PATH = DATA_DIR / "lawdiff-alert-state.json"
FEED_PATH = DATA_DIR / "lawdiff-alerts.json"
TEXT_PATH = DATA_DIR / "lawdiff-alerts.txt"
WINDOW_DAYS = int(os.environ.get("LAWDIFF_ALERT_WINDOW_DAYS", "30"))
MAX_ITEMS = int(os.environ.get("LAWDIFF_ALERT_MAX_ITEMS", "20"))


def _load_state() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return set(data.get("sent_keys", []))


def _save_state(sent_keys: set[str]) -> None:
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "sent_keys": sorted(sent_keys),
    }
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_alert_feed() -> dict:
    since = (date.today() - timedelta(days=WINDOW_DAYS)).strftime("%Y%m%d")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT law_id, law_mst, name, ministry, categories, revision_type, "
        "promulgation_date, enforcement_date "
        "FROM laws "
        "WHERE promulgation_date >= ? "
        "AND revision_type IN ('일부개정', '전부개정', '제정', '폐지') "
        "ORDER BY promulgation_date DESC, law_id DESC LIMIT ?",
        (since, MAX_ITEMS),
    ).fetchall()
    conn.close()

    sent_keys = _load_state()
    next_state = set(sent_keys)
    items = []
    new_items = []

    for row in rows:
        mst = row["law_mst"] or ""
        alert_key = f"{mst}:{row['promulgation_date']}:{row['revision_type']}"
        diff_path = BASE_DIR / "finlaw" / "diff" / mst / "index.html"
        diff_url = f"/finlaw/diff/{mst}/" if mst and diff_path.exists() else ""
        detail_url = f"/finlaw/detail/{row['law_id']}/" if row["law_id"] else ""
        item = {
            "alert_key": alert_key,
            "law_id": row["law_id"],
            "law_mst": mst,
            "name": row["name"],
            "ministry": row["ministry"] or "",
            "categories": row["categories"] or "",
            "revision_type": row["revision_type"] or "",
            "promulgation_date": row["promulgation_date"] or "",
            "enforcement_date": row["enforcement_date"] or "",
            "diff_url": diff_url,
            "detail_url": detail_url,
            "is_new": alert_key not in sent_keys,
        }
        items.append(item)
        if item["is_new"]:
            new_items.append(item)
            next_state.add(alert_key)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "window_days": WINDOW_DAYS,
        "total_recent": len(items),
        "new_alerts": len(new_items),
        "items": items,
    }
    FEED_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"[LawDiff 알림] {payload['generated_at']}",
        f"최근 {WINDOW_DAYS}일 개정 법령 {len(items)}건",
        f"신규 알림 {len(new_items)}건",
        "",
    ]
    for item in new_items or items[:10]:
        link = item["diff_url"] or item["detail_url"] or "/regulation/finlaw/"
        lines.append(
            f"- {item['name']} | {item['revision_type']} | 공포 {item['promulgation_date']} | {link}"
        )
    TEXT_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    _save_state(next_state)
    print(f"[lawdiff_alerts] lawdiff-alerts.json 생성 — 최근 {len(items)}건, 신규 {len(new_items)}건")
    return payload


def main():
    build_alert_feed()


if __name__ == "__main__":
    main()
