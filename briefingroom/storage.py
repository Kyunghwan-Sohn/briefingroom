import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .config import CAT_MAP, DATA_DIR, FINANCE_SUB_MAP


def extract_summary_parts(summary: str) -> tuple[str, list[str], str]:
    """LLM 응답에서 요약, 키워드, 영향도를 추출한다.

    Returns:
        (summary_text, keywords, impact)
        impact는 "상", "중", "하" 중 하나. 파싱 실패 시 "중".
    """
    if not summary:
        return "", [], "중"
    summary_text = ""
    keywords: list[str] = []
    impact = "중"
    for line in summary.splitlines():
        line = line.strip()
        if line.startswith("요약:"):
            summary_text = line.replace("요약:", "", 1).strip()
        elif line.startswith("키워드:"):
            raw = line.replace("키워드:", "", 1)
            keywords = [kw.strip().lstrip("#") for kw in raw.split(",") if kw.strip()]
        elif line.startswith("영향도:"):
            raw_impact = line.replace("영향도:", "", 1).strip()
            if raw_impact in ("상", "중", "하"):
                impact = raw_impact
    return summary_text, keywords, impact


def serialize_item(item: dict) -> dict:
    summary_text, keywords, impact = extract_summary_parts(item.get("summary", ""))
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
        "impact": impact,
        "raw_summary": item.get("summary", ""),
        "has_text": bool(item.get("text")),
        "text_path": item.get("text_path", ""),
    }


def _pick_top3(items: list[dict]) -> list[int]:
    """영향도 기반으로 '오늘의 핵심' 상위 3건의 인덱스를 반환한다.

    선정 기준 (우선순위):
    1. 영향도 "상" > "중" > "하"
    2. 동일 영향도 내에서는 요약이 있는 건 우선
    3. 동일 조건이면 원래 순서(크롤링 순) 유지
    4. 5개 카테고리에서 최대한 다양하게 선정 (같은 카테고리 2건 이상 지양)
    """
    IMPACT_SCORE = {"상": 3, "중": 2, "하": 1}

    scored = []
    for idx, it in enumerate(items):
        score = IMPACT_SCORE.get(it.get("impact", "중"), 2)
        has_summary = 1 if it.get("summary") else 0
        scored.append((score, has_summary, idx))

    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))

    top3 = []
    used_cats = set()
    for score, _, idx in scored:
        if len(top3) >= 3:
            break
        cat = items[idx].get("category", "")
        # 같은 카테고리가 이미 2건이면 다른 카테고리 우선
        cat_count = sum(1 for i in top3 if items[i].get("category") == cat)
        if cat_count >= 2:
            continue
        top3.append(idx)
        used_cats.add(cat)

    # 다양성 제약으로 3건을 못 채웠으면 순수 점수순으로 채움
    if len(top3) < 3:
        for score, _, idx in scored:
            if idx not in top3:
                top3.append(idx)
            if len(top3) >= 3:
                break

    return top3


def save_daily_snapshot(items: Iterable[dict], target: date) -> Path:
    serialized = [serialize_item(item) for item in items]

    # 오늘의 핵심 3건 선정
    top3_indices = _pick_top3(serialized)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target_date": target.isoformat(),
        "count": len(serialized),
        "top3": top3_indices,
        "items": serialized,
    }
    out_path = DATA_DIR / f"{target.isoformat()}.json"

    # U+FFFD 깨진 문자 검출 가드
    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    if "\ufffd" in raw:
        broken_count = raw.count("\ufffd")
        print(f"  [경고] JSON에 깨진 문자 {broken_count}건 발견 → 제거 후 저장")
        raw = raw.replace("\ufffd", "")
    out_path.write_text(raw, encoding="utf-8")

    latest_payload = dict(payload)
    latest_payload["snapshot"] = out_path.name
    (DATA_DIR / "latest.json").write_text(
        json.dumps(latest_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
