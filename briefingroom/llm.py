import json
import time

import requests

from .config import API_KEY, API_URL, MAX_TEXT, MODEL, SYSTEM_PROMPT

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


def summarize(item: dict) -> str:
    global _quota_exhausted
    if _quota_exhausted:
        return "[한도 초과] 다음 실행에서 재처리"
    if not item.get("text"):
        return "[텍스트 없음]"
    text = item["text"][:MAX_TEXT]
    if len(item["text"]) > MAX_TEXT:
        text += "\n\n[이하 생략]"

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"기관: {item['source']}\n제목: {item['title']}\n\n---\n{text}"},
                    ],
                    "stream": False,
                    "temperature": 0.3,
                },
                timeout=120,
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
