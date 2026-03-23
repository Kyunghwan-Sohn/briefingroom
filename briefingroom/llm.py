import time

import requests

from .config import API_KEY, API_URL, MAX_TEXT, MODEL, SYSTEM_PROMPT

MAX_RETRIES = 3


def summarize(item: dict) -> str:
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
                return resp.json()["choices"][0]["message"]["content"].strip()
            if resp.status_code == 429 or resp.status_code >= 500:
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
