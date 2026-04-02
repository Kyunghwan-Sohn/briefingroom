"""보도자료 상세 브리핑 보강 스크립트

3/27 이후 index.html의 간략 요약을 상세 브리핑으로 보강합니다.
1. 원문 URL에서 텍스트 수집
2. LLM으로 상세 분석 생성
3. index.html에 삽입

실행: python -m briefingroom.enrich_articles [날짜] [최대건수]
예: python -m briefingroom.enrich_articles 2026-03-31 20
"""
from __future__ import annotations

import html as html_mod
import os
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from briefingroom.config import BASE_DIR

ARTICLES_DIR = BASE_DIR / "articles"

# .env에서 LLM 키 로드
_env = BASE_DIR / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://abcllm-api.brut.bot/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5:35b")

PROMPT = """당신은 Bloomberg/Reuters 수준의 정책 인텔리전스 애널리스트다.
정부 보도자료 원문을 읽고, 상세 브리핑을 작성하라.

## 출력 규칙 (마크다운, ### 섹션)

### 핵심 요약
- 2~3문장. 핵심 숫자(%, 금액, 건수)와 날짜 포함. 첫 문장은 "누가, 무엇을, 언제".

### 왜 중요한가
- 정확히 1문장. 산업·시장·국민에게 미치는 실질적 파급력.

### 주요 내용
- 불릿(-) 3~5개. 숫자 포함. 각 불릿 1~2문장으로 완결.

### 시행 일정
- 핵심 날짜만. 없으면 섹션 생략.

## 원칙
1. 원문에 없는 내용 추가/추측 금지
2. 해당 정보 없는 섹션은 통째로 생략
3. "획기적", "적극 추진" 등 관료체/홍보체 표현 금지
4. 숫자: 천 단위 쉼표, 금액은 억/조 단위
5. 간결하게. 원문이 짧으면 브리핑도 짧게"""

sess = requests.Session()
sess.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; govbrief.kr/1.0)"})


def fetch_article_text(url: str) -> str:
    """원문 URL에서 본문 텍스트 추출"""
    try:
        r = sess.get(url, timeout=20)
        r.encoding = r.apparent_encoding or "utf-8"
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")

        # 불필요 태그 제거
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # korea.kr 본문
        content = soup.find("div", class_="view_cont") or soup.find("div", class_="article_body")
        if not content:
            content = soup.find("div", id="content") or soup.find("article")
        if not content:
            content = soup.find("main") or soup.body

        if content:
            text = content.get_text(separator="\n", strip=True)
            # 너무 짧으면 전체 body 시도
            if len(text) < 200 and soup.body:
                text = soup.body.get_text(separator="\n", strip=True)
            return text[:10000]
    except Exception as e:
        print(f"    [FETCH ERR] {e}")
    return ""


def llm_analyze(text: str) -> str:
    """LLM 상세 분석"""
    if not LLM_API_KEY or not text:
        return ""
    try:
        r = requests.post(
            LLM_API_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": text[:8000]},
                ],
                "stream": False,
                "options": {"num_ctx": 32768},
            },
            timeout=120,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"    [LLM ERR] {e}")
    return ""


def md_to_html(md: str) -> str:
    """마크다운 → HTML 섹션 변환"""
    sections = []
    current_title = ""
    current_body = []

    for line in md.split("\n"):
        stripped = line.strip()
        if stripped.startswith("### "):
            if current_title and current_body:
                sections.append((current_title, "\n".join(current_body)))
            current_title = stripped[4:]
            current_body = []
        elif stripped:
            current_body.append(stripped)

    if current_title and current_body:
        sections.append((current_title, "\n".join(current_body)))

    html_parts = []
    for title, body in sections:
        css = "info-section"
        if "중요" in title:
            css = "info-section why-box"
        elif "일정" in title:
            css = "info-section impact-box"

        body_html = []
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                body_html.append(f"<p>{html_mod.escape(line)}</p>")
            elif line:
                body_html.append(f"<p>{html_mod.escape(line)}</p>")

        html_parts.append(
            f'<section class="{css}">\n'
            f"  <h3>{html_mod.escape(title)}</h3>\n"
            f'  {"".join(body_html)}\n'
            f"</section>"
        )

    return "\n    ".join(html_parts)


def enrich_date(target_date: str, max_items: int = 200):
    """특정 날짜의 보도자료를 보강"""
    date_dir = ARTICLES_DIR / target_date
    if not date_dir.exists():
        print(f"[enrich] {target_date} 디렉토리 없음")
        return

    art_dirs = sorted(d for d in date_dir.iterdir() if d.is_dir() and (d / "index.html").exists())
    print(f"[enrich] {target_date}: {len(art_dirs)}건 대상")

    enriched = 0
    for art_dir in art_dirs[:max_items]:
        index_path = art_dir / "index.html"
        text = index_path.read_text(encoding="utf-8")

        # 이미 상세 브리핑이 있으면 스킵
        if "왜 중요한가" in text or "주요 내용" in text:
            continue

        # 원문 URL 추출
        m = re.search(r'href="(https?://[^"]+)"[^>]*>원문 보기', text)
        if not m:
            continue

        url = m.group(1)
        slug = art_dir.name
        print(f"  [{slug}] 원문 수집 중... {url[:60]}")

        # 1. 원문 수집
        raw_text = fetch_article_text(url)
        if len(raw_text) < 100:
            print(f"    [SKIP] 원문 부족 ({len(raw_text)}자)")
            time.sleep(0.5)
            continue

        # 2. LLM 분석
        print(f"    LLM 분석 중...")
        analysis = llm_analyze(raw_text)
        if not analysis:
            print(f"    [SKIP] LLM 응답 없음")
            time.sleep(1)
            continue

        # 3. HTML 변환 + 삽입
        detail_html = md_to_html(analysis)
        if not detail_html:
            continue

        # 키워드 div 앞에 삽입
        insert_marker = "    <div class='keywords'>"
        if insert_marker not in text:
            insert_marker = '<div class="links">'
        if insert_marker not in text:
            print(f"    [SKIP] 삽입점 없음")
            continue

        new_text = text.replace(
            insert_marker,
            f"    {detail_html}\n\n    {insert_marker}",
            1,
        )

        index_path.write_text(new_text, encoding="utf-8")
        enriched += 1
        print(f"    [OK] 상세 브리핑 삽입 완료")
        time.sleep(1)

    print(f"\n[enrich] {target_date} 완료: {enriched}건 보강")
    return enriched


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    max_items = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    if target:
        enrich_date(target, max_items)
    else:
        # 3/27 이후 전체
        dates = ["2026-03-27", "2026-03-28", "2026-03-30", "2026-03-31", "2026-04-01"]
        total = 0
        for d in dates:
            total += enrich_date(d, max_items) or 0
        print(f"\n[enrich] 전체 완료: {total}건 보강")


if __name__ == "__main__":
    main()
