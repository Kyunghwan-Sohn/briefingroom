"""보도자료를 Supabase briefings 테이블에 업로드

실행: python -m briefingroom.briefings_upload
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from briefingroom.config import BASE_DIR, DATA_DIR

_env_path = BASE_DIR / ".env.supabase"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def upload_briefings():
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    json_files = sorted(
        [f for f in DATA_DIR.iterdir() if f.name.startswith("2026-") and f.suffix == ".json"
         and "weekly" not in f.name and "schedule" not in f.name
         and "subsidies" not in f.name and "latest" not in f.name],
    )

    total = 0
    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items", data) if isinstance(data, dict) else data

        batch = []
        for idx, it in enumerate(items):
            keywords = it.get("keywords", [])
            if isinstance(keywords, list):
                keywords = ", ".join(keywords)
            batch.append({
                "date": it.get("date", jf.stem),
                "slug": it.get("slug") or f"{idx:03d}",
                "source": it.get("source", ""),
                "title": it.get("title", ""),
                "category": it.get("category", ""),
                "summary": (it.get("summary") or "")[:500],
                "keywords": keywords,
                "impact": it.get("impact", "중"),
                "url": it.get("url", ""),
            })

        if batch:
            for i in range(0, len(batch), 100):
                client.table("briefings").upsert(batch[i:i+100], on_conflict="id").execute()
            total += len(batch)
            print(f"  {jf.stem}: {len(batch)}건")

    print(f"\n[briefings_upload] 전체 {total}건 업로드 완료")
    return total


def main():
    upload_briefings()


if __name__ == "__main__":
    main()
