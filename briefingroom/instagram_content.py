"""인스타그램 캐러셀 콘텐츠 생성 (LLM 기반)

top3로 선정된 보도자료의 원문 붙임자료(PDF/HWP)를 직접 다운로드하여
텍스트 전문을 추출한 뒤, LLM으로 인스타 카드뉴스용 구조화 콘텐츠를 생성한다.
이미지 생성 전에 미리보기로 확인할 수 있다.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path

import requests

from briefingroom.config import API_KEY, API_URL, DATA_DIR, MODEL
from briefingroom.crawlers.common import new_session
from briefingroom.files import download_file, extract_hwp, extract_pdf

IG_CONTENT_PROMPT = """\
당신은 맥킨지 출신 정책 전문 애널리스트이자 인스타그램 콘텐츠 디렉터다.
복잡한 정부 정책을 일반인이 바로 이해하도록 풀어쓰는 전문가다.

# 임무

정부 보도자료 원문을 인스타그램 캐러셀 4장 구성으로 변환하라.
반드시 아래 JSON 형식으로만 답하라.

```json
{
  "hook": "표지 제목 (7~15자, 호기심 유발)",
  "subtitle": "보조 설명 (10~25자)",

  "summary": {
    "points": [
      {"label": "핵심 포인트 제목 (5~12자)", "text": "구체적 설명 (40~80자)", "stat": "수치 하나 (예: 2.1만명, +61%)"},
      {"label": "두 번째 포인트 제목", "text": "구체적 설명", "stat": "수치 하나"},
      {"label": "세 번째 포인트 제목", "text": "구체적 설명", "stat": "수치 하나"}
    ]
  },

  "article": "보도자료 내용을 쉽게 풀어쓴 기사 (250~400자). 원문의 핵심 사실을 일반인이 읽기 편한 문장으로 재구성. 전문용어는 괄호 안에 풀이.",

  "analysis": {
    "positive": "이 정책의 긍정적 효과 (60~120자). 누구에게 어떤 이익이 되는지 구체적으로.",
    "concern": "우려되는 점 또는 한계 (60~120자). 시행 과정에서 예상되는 문제나 보완 필요 사항.",
    "outlook": "향후 전망 (60~120자). 이 정책이 앞으로 어떻게 발전하거나 확대될지."
  },

  "hashtags": ["정책키워드", "관련분야", "정책브리핑"]
}
```

# 슬라이드 4장 구성

## 슬라이드 1: 핵심 요약 (hook + summary)
- hook: 스크롤 멈추는 제목. "~, 뭐가 달라지나?" / "~, 핵심 3가지" 등
- summary.points 3개: 보도자료의 핵심 내용을 한 장에 일목요연하게
- 각 point의 stat: 가장 임팩트 있는 수치 1개 (금액/비율/인원/날짜)

## 슬라이드 2: 보도자료 기사 (article)
- 보도자료 원문의 핵심 내용을 기사처럼 쉽게 풀어서 작성
- 일반인이 "아, 이런 내용이구나" 하고 5분 안에 이해할 수 있는 수준
- 전문용어는 반드시 괄호 안에 풀이
- 구체적 수치/날짜/대상을 빠짐없이 포함

## 슬라이드 3: 효과/영향 분석 (analysis)
- positive: 이 정책으로 좋아지는 점 (구체적 수혜 대상, 기대 효과)
- concern: 우려 사항이나 한계점 (객관적 시각, 비판이 아닌 건설적 분석)
- outlook: 향후 전망 (확대 계획, 후속 조치, 업계 반응 등)

## 슬라이드 4: 참여 유도
- 시스템이 자동 생성 (JSON에 포함 불필요)
- "이 정책, 어떻게 생각하시나요?" + 의견 요청

# 작성 규칙

1. 원문에 없는 내용 절대 작성 금지 (analysis도 원문 기반으로만)
2. 장관/차관 이름 언급 금지
3. "~했다", "~밝혔다" 뉴스 기사체 금지 → "~입니다", "~됩니다" 설명체
4. "적극 추진", "대폭 강화" 등 정부 홍보 문구 금지
5. 모든 글자 수 제한 엄수
6. stat은 절대 비워두지 마라
"""

MAX_TEXT_FOR_IG = 5000  # LLM에 보낼 원문 최대 길이


# ── 원문 전문 추출 ────────────────────────────────────────────

def fetch_full_text(item: dict) -> str:
    """top3 기사의 붙임자료(PDF/HWP)를 직접 다운로드하여 텍스트 전문을 추출한다.

    텍스트 확보 우선순위:
    1. 로컬 texts/ 디렉토리에 이미 추출된 파일이 있으면 사용
    2. 없으면 PDF URL에서 직접 다운로드 + 추출
    3. PDF 실패 시 HWP URL에서 다운로드 + 추출
    4. 첨부파일 없으면 body_text 또는 웹페이지에서 본문 추출
    """
    # 1단계: 로컬 텍스트 파일 검색
    local_text = _find_local_text(item)
    if local_text and len(local_text) >= 200:
        print(f"    [원문] 로컬 텍스트 사용 ({len(local_text)}자)")
        return local_text

    # 2단계: 첨부파일 직접 다운로드 + 추출
    session = new_session()
    src = re.sub(r"[^\w가-힣]", "", item.get("source", ""))[:4]
    safe = re.sub(r"[^\w가-힣]", "_", item.get("title", ""))[:30]
    file_texts = []

    # PDF 전부 다운로드 + 추출
    for i, url in enumerate(item.get("pdfs", []), 1):
        fname = f"ig_{item.get('date', '')}_{src}_{safe}_{i}.pdf"
        path = download_file(url, fname, session)
        if path:
            text = extract_pdf(path)
            if text and len(text) > 50:
                file_texts.append(text)
        time.sleep(0.3)

    # PDF 실패 시 HWP
    if not file_texts:
        for j, url in enumerate(item.get("hwps", []), 1):
            ext = "hwpx" if "hwpx" in url.lower() else "hwp"
            fname = f"ig_{item.get('date', '')}_{src}_{safe}_{j}.{ext}"
            path = download_file(url, fname, session)
            if path:
                text = extract_hwp(path)
                if text and len(text) > 50:
                    file_texts.append(text)
            time.sleep(0.3)

    if file_texts:
        full_text = "\n\n".join(file_texts)
        print(f"    [원문] 첨부파일 추출 완료 ({len(full_text)}자, 파일 {len(file_texts)}개)")
        return full_text

    # 3단계: 웹페이지 본문 추출 (fallback)
    url = item.get("url", "")
    if url:
        try:
            from bs4 import BeautifulSoup
            r = session.get(url, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                for sel in ["div.view_cont", "div.article_view", "article",
                            "div.content", "div#cont_view", "main"]:
                    el = soup.select_one(sel)
                    if el and len(el.get_text(strip=True)) > 100:
                        body = re.sub(r"\s+", " ", el.get_text(strip=True))[:8000]
                        print(f"    [원문] 웹페이지 본문 추출 ({len(body)}자)")
                        return body
        except Exception as e:
            print(f"    [원문] 웹 추출 실패: {e}")

    # 4단계: 기존 summary만 있는 경우
    summary = item.get("summary", "")
    if summary:
        print(f"    [원문] 요약만 사용 ({len(summary)}자) — 품질 제한적")
        return summary

    print(f"    [원문] 텍스트 확보 실패")
    return ""


def _find_local_text(item: dict) -> str:
    """로컬 texts/ 디렉토리에서 해당 기사의 텍스트 파일을 검색한다."""
    # text_path가 있으면 직접 시도
    text_path = item.get("text_path", "")
    if text_path:
        p = Path(text_path)
        if p.exists():
            return p.read_text(encoding="utf-8")

    # texts/ 디렉토리에서 날짜+부처+제목으로 검색
    from briefingroom.config import BASE_DIR
    texts_dir = BASE_DIR / "texts"
    if not texts_dir.exists():
        return ""

    date_str = item.get("date", "")
    source = item.get("source", "")
    title = item.get("title", "")
    if not date_str or not source:
        return ""

    source_short = source[:4]
    title_clean = re.sub(r'[^\w가-힣]', '', title[:10])

    for f in texts_dir.iterdir():
        if not f.name.startswith(date_str):
            continue
        if source_short not in f.name:
            continue
        fname_clean = re.sub(r'[^\w가-힣]', '', f.name)
        if title_clean and title_clean in fname_clean:
            return f.read_text(encoding="utf-8")

    return ""


# ── LLM 콘텐츠 생성 ──────────────────────────────────────────

def generate_carousel_content(item: dict) -> dict | None:
    """보도자료 원문에서 인스타 카드뉴스용 콘텐츠를 생성한다.

    1. 원문 전문을 확보한다 (첨부파일 다운로드 포함)
    2. LLM으로 구조화된 콘텐츠를 생성한다
    3. 실패 시 fallback을 반환한다
    """
    # 1단계: 원문 전문 확보
    full_text = fetch_full_text(item)

    if not full_text or len(full_text) < 100:
        print(f"    [IG Content] 원문 부족 → fallback")
        return _fallback_from_summary(item)

    # 2단계: LLM 호출
    source = item.get("source", "")
    title = item.get("title", "")

    text_truncated = full_text[:MAX_TEXT_FOR_IG]
    if len(full_text) > MAX_TEXT_FOR_IG:
        text_truncated += "\n\n[이하 생략]"

    user_msg = f"기관: {source}\n제목: {title}\n\n---\n{text_truncated}"

    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": IG_CONTENT_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "stream": False,
                "temperature": 0.3,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            print(f"    [IG Content] LLM 오류 HTTP {resp.status_code}")
            return _fallback_from_summary(item)

        raw = resp.json()["choices"][0]["message"]["content"].strip()
        return _parse_content(raw, item)

    except Exception as e:
        print(f"    [IG Content] LLM 호출 실패: {e}")
        return _fallback_from_summary(item)


def _parse_content(raw: str, item: dict) -> dict | None:
    """LLM 응답에서 JSON 콘텐츠를 파싱한다."""
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        print(f"    [IG Content] JSON 파싱 실패")
        return _fallback_from_summary(item)

    try:
        content = json.loads(json_match.group())
    except json.JSONDecodeError:
        print(f"    [IG Content] JSON 디코드 실패")
        return _fallback_from_summary(item)

    if "points" not in content or len(content.get("points", [])) < 2:
        print(f"    [IG Content] 포인트 부족")
        return _fallback_from_summary(item)

    # 원본 메타 정보 보강
    content["source"] = item.get("source", "")
    content["title"] = item.get("title", "")
    content["date"] = item.get("date", "")
    content["category"] = item.get("category", "")
    content["impact"] = item.get("impact", "중")
    content["keywords"] = item.get("keywords", [])

    return content


def _fallback_from_summary(item: dict) -> dict:
    """요약만 있을 때 fallback 콘텐츠 생성"""
    summary = item.get("summary", "")
    sentences = re.split(r'(?<=[.다])\s+', summary) if summary else []

    points = []
    for i, sent in enumerate(sentences[:3]):
        sent = sent.strip()
        if len(sent) < 10:
            continue
        points.append({
            "title": f"핵심 {i+1}",
            "detail": sent[:80],
            "highlight": "",
        })

    if not points:
        points = [{"title": "핵심 내용", "detail": summary[:80] if summary else "내용 없음", "highlight": ""}]

    return {
        "hook": item.get("title", "")[:15],
        "subtitle": "핵심 내용을 정리했습니다",
        "points": points,
        "impact_line": "",
        "hashtags": item.get("keywords", [])[:3],
        "source": item.get("source", ""),
        "title": item.get("title", ""),
        "date": item.get("date", ""),
        "category": item.get("category", ""),
        "impact": item.get("impact", "중"),
        "keywords": item.get("keywords", []),
        "_is_fallback": True,
    }


# ── 미리보기 ──────────────────────────────────────────────────

def preview_daily_content(target: date | str) -> list[dict]:
    """일일 JSON에서 top3 기사의 원문을 확보하고 인스타 콘텐츠를 미리보기한다."""
    if isinstance(target, str):
        target = date.fromisoformat(target)

    json_path = DATA_DIR / f"{target.isoformat()}.json"
    if not json_path.exists():
        print(f"  [Instagram] JSON 없음: {json_path}")
        return []

    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        print("  [Instagram] 기사 0건 → 스킵")
        return []

    top3_indices = data.get("top3", [])
    if not top3_indices:
        scored = []
        for i, it in enumerate(items):
            imp_score = {"상": 3, "중": 2, "하": 1}.get(it.get("impact", "중"), 2)
            has_sum = 1 if it.get("summary") else 0
            scored.append((imp_score, has_sum, i))
        scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
        top3_indices = [s[2] for s in scored[:3]]

    results = []
    for rank, idx in enumerate(top3_indices):
        if idx >= len(items):
            continue
        item = items[idx]
        if not item.get("summary"):
            continue

        print(f"\n{'━' * 60}")
        print(f"  #{rank+1} [{item['source']}] {item['title'][:50]}")
        print(f"{'━' * 60}")

        content = generate_carousel_content(item)
        if content:
            results.append(content)
            _print_preview(content)
            time.sleep(1)

    return results


def _print_preview(content: dict):
    """콘텐츠를 텍스트로 미리보기 출력"""
    is_fallback = content.get("_is_fallback", False)
    label = "⚠️ FALLBACK (요약 기반)" if is_fallback else "✅ LLM 생성 (원문 기반)"

    print(f"\n  [{label}]")
    print(f"  ┌─ 표지 ─────────────────────────────────────")
    print(f"  │ 부처: {content.get('source', '')}")
    print(f"  │ Hook: {content.get('hook', '')}")
    print(f"  │ 부제: {content.get('subtitle', '')}")
    print(f"  │")

    for i, pt in enumerate(content.get("points", [])):
        print(f"  ├─ POINT {i+1:02d} ──────────────────────────────")
        print(f"  │ 제목: {pt.get('title', '')}")
        print(f"  │ 설명: {pt.get('detail', '')}")
        hl = pt.get('highlight', '')
        print(f"  │ 강조: {hl if hl else '(없음)'}")
        print(f"  │")

    print(f"  ├─ CTA ───────────────────────────────────────")
    print(f"  │ 임팩트: {content.get('impact_line', '') or '(없음)'}")
    tags = ' '.join('#' + t for t in content.get('hashtags', []))
    print(f"  │ 해시태그: {tags}")
    print(f"  └─────────────────────────────────────────────")


if __name__ == "__main__":
    import sys
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    print(f"\n  인스타그램 콘텐츠 미리보기 | {target_date}")
    print(f"  {'=' * 56}\n")
    results = preview_daily_content(target_date)
    print(f"\n\n  총 {len(results)}건의 콘텐츠 생성 완료")
    for r in results:
        fb = " (fallback)" if r.get("_is_fallback") else ""
        print(f"    [{r['source']}] {r['hook']}{fb}")
