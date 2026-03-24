import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .config import CAT_MAP, DATA_DIR, FINANCE_SUB_MAP


def extract_summary_parts(summary: str) -> tuple[str, list[str]]:
    if not summary:
        return "", []
    summary_text = ""
    keywords: list[str] = []
    for line in summary.splitlines():
        line = line.strip()
        if line.startswith("요약:"):
            summary_text = line.replace("요약:", "", 1).strip()
        elif line.startswith("키워드:"):
            raw = line.replace("키워드:", "", 1)
            keywords = [kw.strip().lstrip("#") for kw in raw.split(",") if kw.strip()]
    return summary_text, keywords


def serialize_item(item: dict) -> dict:
    summary_text, keywords = extract_summary_parts(item.get("summary", ""))
    return {
        "source": item.get("source", ""),
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "date": item.get("date", ""),
        "category": CAT_MAP.get(item.get("source", ""), "행정법제"),
        "finance_sub": FINANCE_SUB_MAP.get(item.get("source", ""), ""),
        "pdfs": item.get("pdfs", []),
        "hwps": item.get("hwps", []),
        "files": item.get("files", []),
        "summary": summary_text,
        "keywords": keywords,
        "raw_summary": item.get("summary", ""),
        "has_text": bool(item.get("text")),
        "text_path": item.get("text_path", ""),
    }


def save_daily_snapshot(items: Iterable[dict], target: date) -> Path:
    serialized = [serialize_item(item) for item in items]
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target_date": target.isoformat(),
        "count": len(serialized),
        "items": serialized,
    }
    out_path = DATA_DIR / f"{target.isoformat()}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_payload = dict(payload)
    latest_payload["snapshot"] = out_path.name
    (DATA_DIR / "latest.json").write_text(
        json.dumps(latest_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
