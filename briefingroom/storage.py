import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .config import CAT_MAP, DATA_DIR, FINANCE_SUB_MAP


def extract_summary_parts(summary: str) -> tuple[str, list[str], str]:
    """LLM 응답에서 요약, 키워드, 영향도를 추출한다.

    LLM이 '요약:  \\n내용...' 처럼 줄바꿈 후 내용을 쓰는 경우도 처리한다.

    Returns:
        (summary_text, keywords, impact)
        impact는 "상", "중", "하" 중 하나. 파싱 실패 시 "중".
    """
    if not summary:
        return "", [], "중"

    # 섹션 기반 파싱: "요약:", "키워드:", "영향도:" 를 구분자로 분할
    import re
    summary_text = ""
    keywords: list[str] = []
    impact = "중"

    # 각 섹션의 시작 위치 찾기
    markers = []
    for m in re.finditer(r'^(요약|키워드|영향도):', summary, re.MULTILINE):
        markers.append((m.start(), m.group(1), m.end()))

    if not markers:
        # 마커가 하나도 없으면 전체를 요약으로 취급
        return summary.strip(), [], "중"

    for i, (start, label, content_start) in enumerate(markers):
        # 이 섹션의 끝 = 다음 마커의 시작 또는 문자열 끝
        end = markers[i + 1][0] if i + 1 < len(markers) else len(summary)
        content = summary[content_start:end].strip()

        if label == "요약":
            summary_text = content
        elif label == "키워드":
            keywords = [kw.strip().lstrip("#") for kw in content.split(",") if kw.strip()]
        elif label == "영향도":
            val = content.split()[0] if content else ""
            if val in ("상", "중", "하"):
                impact = val

    # "[텍스트 없음]" 등 실패 마커는 빈 요약으로 처리
    _fail_markers = ("[텍스트 없음]", "[한도 초과]", "[오류]")
    if summary_text.startswith(_fail_markers):
        summary_text = ""

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
