import json
import time

import requests

from .config import API_KEY, API_URL, MAX_TEXT, MODEL, SYSTEM_PROMPT, WEEKLY_SIGNAL_PROMPT, WEEKLY_REPORT_PROMPT, LAW_ANALYSIS_PROMPT

MAX_RETRIES = 3
_quota_exhausted = False  # 일일 한도 초과 플래그


def _parse_response(resp: requests.Response) -> str:
    """스트리밍/비스트리밍 응답 모두 처리"""
    content_type = resp.headers.get("Content-Type", "")

    # 스트리밍 응답 처리 (text/event-stream)
    if "event-stream" in content_type or resp.text.startswith("data:"):
        collected = []
        for line in resp.text.splitlines():
            line = line.strip()
            if not line or line == "data: [DONE]":
                continue
            if line.startswith("data:"):
                try:
                    chunk = json.loads(line[5:].strip())
                    delta = chunk["choices"][0]["delta"]
                    if delta.get("content"):
                        collected.append(delta["content"])
                except Exception:
                    continue
        return "".join(collected).strip()

    # 일반 JSON 응답
    try:
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[파싱 실패] {e}"


def _chat_completion(messages: list[dict], temperature: float = 0.3) -> str:
    global _quota_exhausted
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": MODEL,
                    "messages": messages,
                    "stream": False,
                    "temperature": temperature,
                    "options": {"num_ctx": 65536},
                },
                timeout=180,
            )
            if resp.status_code == 200:
                return _parse_response(resp)
            if resp.status_code == 429:
                # 일일 한도 초과 감지 → 이후 건 전부 스킵
                body = resp.text.lower()
                if "quota" in body or "daily" in body:
                    _quota_exhausted = True
                    print(f"    [LLM] 일일 한도 초과 — 나머지 건은 다음 실행에서 재처리")
                    return "[한도 초과] 다음 실행에서 재처리"
                wait = 2 ** attempt * 5
                print(f"    [LLM 재시도] HTTP 429, {wait}초 대기 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = 2 ** attempt * 5
                print(f"    [LLM 재시도] HTTP {resp.status_code}, {wait}초 대기 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            return f"[오류] HTTP {resp.status_code}"
        except (requests.ConnectionError, requests.Timeout) as e:
            wait = 2 ** attempt * 5
            print(f"    [LLM 재시도] {e}, {wait}초 대기 ({attempt+1}/{MAX_RETRIES})")
            time.sleep(wait)
        except Exception as e:
            return f"[요약 실패] {e}"
    return "[한도 초과] 재시도 모두 실패"


REVIEW_PROMPT = """당신은 정부 보도자료 요약의 품질 검수 편집자입니다.
아래 초안을 검수하여 동일한 형식으로 교정본을 출력하세요.

검수 기준:
1. 오탈자, 띄어쓰기 오류를 모두 수정
2. 불필요한 특수문자(★, ●, ■, ▶, ※, 「」 등) 제거
3. "~할 것으로 보인다", "~에 기여할 전망" 같은 관료체 표현을 직접적 표현으로 교체
4. 쉬운요약은 중학생이 읽어도 이해할 수 있는 수준인지 확인. 전문 용어가 설명 없이 쓰였으면 괄호 설명 추가
5. 숫자, 날짜, 고유명사의 정확성 확인 (원문과 다르면 수정하지 말고 그대로 유지)
6. 각 섹션(요약, 쉬운요약, 핵심포인트, 상세분석, 왜 알아야 하나, 그래서 뭐가 달라지나, 키워드, 영향도)의 형식이 맞는지 확인
7. 내용을 추가하거나 삭제하지 않음. 표현만 다듬음

반드시 동일한 형식(요약: ... 쉬운요약: ... 핵심포인트: ... 상세분석: ... 왜 알아야 하나: ... 그래서 뭐가 달라지나: ... 키워드: ... 영향도: ...)으로만 출력하세요.
다른 말은 하지 마세요."""


def summarize(item: dict) -> str:
    global _quota_exhausted
    if _quota_exhausted:
        return "[한도 초과] 다음 실행에서 재처리"

    text = item.get("text", "")
    if not text:
        text = "(본문 없음. 제목만으로 요약해주세요.)"

    text = text[:MAX_TEXT]
    if len(item.get("text", "")) > MAX_TEXT:
        text += "\n\n[이하 생략]"

    # 1차: 초안 생성
    draft = _chat_completion(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"기관: {item['source']}\n제목: {item['title']}\n\n---\n{text}"},
        ],
        temperature=0.3,
    )

    if not draft or draft.startswith("["):
        return draft

    # 2차: 교정 (오탈자, 띄어쓰기, 관료체 제거, 쉬운요약 품질 확인)
    if _quota_exhausted:
        return draft

    reviewed = _chat_completion(
        [
            {"role": "system", "content": REVIEW_PROMPT},
            {"role": "user", "content": f"[원문 제목] {item['title']}\n[원문 기관] {item['source']}\n\n[초안]\n{draft}"},
        ],
        temperature=0.1,
    )

    if not reviewed or reviewed.startswith("["):
        return draft  # 교정 실패 시 초안 사용

    return reviewed


def analyze_law_change(payload: dict) -> dict:
    """법령 개정 내용을 전문가 관점에서 분석한다."""
    response = _chat_completion(
        [
            {"role": "system", "content": LAW_ANALYSIS_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.3,
    )

    result = {"background": "", "changes": [], "impact": "", "target": "", "penalty": "", "keywords": []}
    if not response or response.startswith("["):
        return result

    import re
    markers = []
    for m in re.finditer(r'^(개정배경|핵심변경|실무영향|대상기업|위반시제재|관련키워드):', response, re.MULTILINE):
        markers.append((m.start(), m.group(1), m.end()))

    for i, (start, label, content_start) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(response)
        content = response[content_start:end].strip()

        if label == "개정배경":
            result["background"] = content
        elif label == "핵심변경":
            changes = [line.strip().lstrip("- ").strip() for line in content.split("\n") if line.strip().startswith("-")]
            result["changes"] = [c for c in changes if c]
        elif label == "실무영향":
            result["impact"] = content
        elif label == "대상기업":
            result["target"] = content
        elif label == "위반시제재":
            result["penalty"] = content
        elif label == "관련키워드":
            result["keywords"] = [kw.strip() for kw in content.split(",") if kw.strip()]

    return result


def generate_weekly_report(payload: dict) -> dict:
    """주간 데이터를 바탕으로 종합 보고서를 생성한다."""
    response = _chat_completion(
        [
            {"role": "system", "content": WEEKLY_REPORT_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.3,
    )

    result = {"summary": "", "sectors": {}, "comparison": "", "outlook": "", "key_figures": []}
    if not response or response.startswith("["):
        return result

    import re
    markers = []
    for m in re.finditer(r'^(주간요약|분야별동향|전주대비|향후전망|핵심수치):', response, re.MULTILINE):
        markers.append((m.start(), m.group(1), m.end()))

    for i, (start, label, content_start) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(response)
        content = response[content_start:end].strip()

        if label == "주간요약":
            result["summary"] = content
        elif label == "분야별동향":
            for line in content.split("\n"):
                line = line.strip().lstrip("- ")
                if ":" in line:
                    sector, desc = line.split(":", 1)
                    result["sectors"][sector.strip()] = desc.strip()
        elif label == "전주대비":
            result["comparison"] = content
        elif label == "향후전망":
            result["outlook"] = content
        elif label == "핵심수치":
            for line in content.split("\n"):
                line = line.strip().lstrip("- ")
                if ":" in line:
                    name, val = line.split(":", 1)
                    result["key_figures"].append({"name": name.strip(), "value": val.strip()})

    return result


def generate_weekly_signals(payload: dict) -> list[dict]:
    """주간 집계 데이터를 바탕으로 정책 시그널 5개를 생성한다."""
    response = _chat_completion(
        [
            {"role": "system", "content": WEEKLY_SIGNAL_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.2,
    )
    try:
        signals = json.loads(response)
        if isinstance(signals, list):
            normalized = []
            for signal in signals[:5]:
                if not isinstance(signal, dict):
                    continue
                normalized.append(
                    {
                        "title": str(signal.get("title", "")).strip(),
                        "evidence": str(signal.get("evidence", "")).strip(),
                        "related_title": str(signal.get("related_title", "")).strip(),
                    }
                )
            if normalized:
                return normalized
    except Exception:
        pass
    return []
