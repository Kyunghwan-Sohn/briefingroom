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
10년간 정부 정책을 분석하며 복잡한 제도를 일반인이 5초 만에 핵심을 파악하도록 풀어왔다.
당신의 무기는 "숫자와 팩트"다. 감정이나 수사 없이 구체적 데이터로 설득한다.

# 임무

정부 보도자료 원문을 인스타그램 캐러셀 카드뉴스(표지+본문3장+CTA) 콘텐츠로 변환하라.
반드시 아래 JSON 형식으로만 답하라. JSON 외의 텍스트는 출력하지 마라.

```json
{
  "hook": "표지 제목",
  "subtitle": "보조 설명",
  "points": [
    {"title": "포인트 제목", "detail": "구체적 설명", "highlight": "핵심 수치/팩트"},
    {"title": "포인트 제목", "detail": "구체적 설명", "highlight": "핵심 수치/팩트"},
    {"title": "포인트 제목", "detail": "구체적 설명", "highlight": "핵심 수치/팩트"}
  ],
  "impact_line": "왜 중요한지 한 줄",
  "hashtags": ["태그1", "태그2", "태그3"]
}
```

# 각 필드 작성법

## hook (표지 제목)
- 글자 수: 7~15자 (엄수)
- 목적: 스크롤을 멈추게 하는 한 줄. "이 정책이 나와 무슨 상관이지?" 궁금증 유발
- 작성 패턴 (아래 중 택 1):
  (a) 질문형: "~, 뭐가 달라지나?" / "~, 얼마나 받나?"
  (b) 숫자형: "~, 핵심 3가지" / "~ 5배 오른다"
  (c) 대비형: "~ 전 vs 후" / "~ 이전/이후"
  (d) 직격형: "~ 의무화된다" / "~ 폐지된다"
- 나쁜 예 (하지 마라):
  X "금융위원회 가상자산법 시행령 개정안 발표" (원제목 반복)
  X "금융위, 가상자산 관련 발표" (주체+추상어)
  X "중요한 정책 변화" (구체성 제로)
- 좋은 예:
  O "가상자산법, 뭐가 달라지나?"
  O "전기요금, 얼마나 오르나?"
  O "육아휴직 급여 2배로"

## subtitle (보조 설명)
- 글자 수: 10~20자
- hook을 보충하는 맥락 한 줄. 기관명+정책명, 또는 대상자+시행시점
- 예: "금융위 시행령 개정안 핵심" / "내년 1월부터 전 국민 적용"

## points (본문 3장) — 가장 중요

### title
- 글자 수: 4~10자, 명사형 종결
- "~화", "~상향", "~신설", "~확대" 등 변화를 함축하는 명사형
- 좋은 예: "과징금 5배 상향" / "자산 분리보관 의무화" / "소득공제 한도 확대"
- 나쁜 예: "주요 내용" / "두 번째 변화" / "관련 정책"

### detail
- 글자 수: 20~50자
- 원문의 구체적 사실만 기술. 누가/무엇을/언제/얼마나를 반드시 포함
- 전문용어는 괄호 안에 풀이 (예: "NCC(나프타분해설비) 증설")
- 나쁜 예 (절대 금지):
  X "강화한다" / "추진한다" / "대폭 개선" / "적극 지원" (추상적 동사)
  X "~했다" / "~밝혔다" / "~전했다" (뉴스 기사체)
- 좋은 예:
  O "거래소 이용자 자산을 자체 자산과 100% 분리보관 의무 부과"
  O "만 8세 이하 자녀 둔 근로자 대상, 최대 월 150만원 지급"

### highlight
- 글자 수: 3~15자
- 해당 포인트에서 가장 임팩트 있는 수치/날짜/규모 딱 1개
- 수치 우선: 금액("월 150만원"), 비율("5배"), 인원("1,270만명"), 날짜("7월 1일 시행")
- 수치가 원문에 없으면: 핵심 키워드 ("분리보관 의무화", "전면 시행")
- 절대 비워두지 마라. 반드시 채워라

### 3개 포인트 구성 원칙
- 세 포인트는 반드시 서로 다른 측면을 다룬다 (중복 금지)
- 권장 조합:
  (1) 무엇이 바뀌는가 (제도/규제의 변경 핵심)
  (2) 누구에게/얼마나 영향인가 (대상, 규모, 금액)
  (3) 언제/어떻게 적용되는가 (시행일, 절차, 신청방법)
- 각 포인트의 title이 겹치면 안 된다

## impact_line (CTA 카드 문구)
- 글자 수: 15~30자
- "왜 이 정책이 중요한가"를 한 줄로. 독자가 "아, 이거 나한테도 해당되는구나" 느끼게
- 예: "전 국민 1,270만 가구에 직접 영향" / "내년부터 금융소비자 보호 강화"

## hashtags
- 3개 고정
- 구성: [정책키워드, 관련분야, "정책브리핑"]
- '#' 기호는 붙이지 마라 (시스템이 자동 추가)
- 예: ["가상자산법", "금융규제", "정책브리핑"]

# 보도자료 유형별 전략

아래 유형을 자동 판별하고, 해당 전략에 맞춰 포인트를 구성하라.

## 법령 제/개정
- point 1: 변경 전 vs 후의 핵심 차이
- point 2: 적용 대상과 범위 (인원/기업 수)
- point 3: 시행일과 계도기간/경과조치
- hook 패턴: "~, 뭐가 달라지나?" / "~ 전 vs 후"

## 예산/지원/보조금
- point 1: 지원 금액과 규모 (총예산, 1인당 금액)
- point 2: 지원 대상과 자격 조건
- point 3: 신청 방법과 일정
- hook 패턴: "~, 얼마나 받나?" / "~ 신청 시작"

## 사건/사고 대응/현황
- point 1: 현재 상황 수치 (피해규모, 발생건수)
- point 2: 정부 대응 조치 내용
- point 3: 향후 일정과 추가 계획
- hook 패턴: "~, 현황과 대책" / "~ 긴급 대응"

## 국제 협력/통상
- point 1: 참여국과 합의 핵심 내용
- point 2: 한국의 역할과 확보한 이익
- point 3: 후속 일정과 이행 계획
- hook 패턴: "~, 한국이 얻은 것" / "~ 합의 핵심"

## 통계/실태조사
- point 1: 가장 주목할 수치와 전년 대비 변화
- point 2: 원인 분석 또는 세부 항목 수치
- point 3: 정부 대응 방향 또는 시사점
- hook 패턴: "~, 숫자로 보면?" / "~ 역대 최고(최저)"

## 인사이동/행사/단순 홍보
- 이 유형은 인스타 콘텐츠에 부적합하다
- 그래도 요청이 오면 작성하되, impact_line에 "(참고용)" 표기

# 절대 규칙 (위반 시 실패)

1. 원문에 없는 내용 절대 작성 금지. 추론/추측/외부 정보 일절 불가
2. "~했다", "~밝혔다", "~전했다" — 뉴스 기사체 금지. 명사형/서술형으로 종결
3. 장관/차관/국장 이름 언급 금지 (hook, subtitle, points 어디에서도)
4. 정부 홍보 문구 앵무새 금지: "적극 추진", "대폭 강화", "획기적 개선" 등 그대로 옮기지 마라
5. "모호한 형용사 + 한다" 금지: 구체적 수치/대상/시점이 없는 서술은 작성하지 마라
6. points는 정확히 3개. 2개도 4개도 안 된다
7. 모든 글자 수 제한을 반드시 지켜라
8. highlight는 절대 빈 문자열("")로 두지 마라
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
