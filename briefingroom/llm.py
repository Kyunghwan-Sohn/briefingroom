import requests

from .config import API_KEY, API_URL, MAX_TEXT, MODEL, SYSTEM_PROMPT


def summarize(item: dict) -> str:
    if not item.get("text"):
        return "[텍스트 없음]"
    text = item["text"][:MAX_TEXT]
    if len(item["text"]) > MAX_TEXT:
        text += "\n\n[이하 생략]"
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
        if resp.status_code == 429:
            return "[한도 초과]"
        if resp.status_code != 200:
            return f"[오류] HTTP {resp.status_code}"
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[요약 실패] {e}"
