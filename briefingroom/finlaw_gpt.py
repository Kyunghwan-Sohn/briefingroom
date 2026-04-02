"""FinLaw GPT — 금융법령 AI 어시스턴트

Supabase FTS 검색 + 자체 LLM으로 RAG 답변 생성.
프론트에서 AJAX 호출용 또는 CLI 테스트용.

사용: python -m briefingroom.finlaw_gpt "자본시장법상 불공정거래 요건은?"
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
try:
    from supabase import create_client
except ImportError:  # pragma: no cover - optional local dependency
    create_client = None

from briefingroom.config import BASE_DIR

# 환경변수 로드
_env_path = BASE_DIR / ".env.supabase"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_env_main = BASE_DIR / ".env"
if _env_main.exists():
    for line in _env_main.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://abcllm-api.brut.bot/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5:35b")

_client = None


def _source_counts(context: dict) -> dict:
    return {
        "laws": len(context.get("laws", [])),
        "articles": len(context.get("articles", [])),
        "precedents": len(context.get("precedents", [])),
        "interpretations": len(context.get("interpretations", [])),
    }


def _get_supabase():
    global _client
    if create_client is None:
        raise RuntimeError("supabase 패키지가 설치되지 않았습니다")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL 또는 SUPABASE_SERVICE_KEY가 설정되지 않았습니다")
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def search_context(query: str, max_results: int = 5) -> dict:
    """Supabase에서 관련 법령/조문/판례 검색"""
    client = _get_supabase()
    context = {"laws": [], "articles": [], "precedents": [], "interpretations": [], "errors": []}

    searches = [
        (
            "laws",
            "search_laws",
            lambda rows: [{
                "name": d["name"],
                "ministry": d.get("ministry", ""),
                "revision_type": d.get("revision_type", ""),
                "amendment_reason": (d.get("amendment_reason") or "")[:200],
            } for d in rows],
        ),
        (
            "articles",
            "search_articles",
            lambda rows: [{
                "article_title": d.get("article_title", ""),
                "content": (d.get("content") or "")[:300],
            } for d in rows],
        ),
        (
            "precedents",
            "search_precedents",
            lambda rows: [{
                "case_name": d["case_name"],
                "court": d.get("court", ""),
                "decision_date": d.get("decision_date", ""),
                "summary": (d.get("summary") or "")[:200],
            } for d in rows],
        ),
        (
            "interpretations",
            "search_interpretations",
            lambda rows: [{
                "title": d["title"],
                "summary": (d.get("summary") or "")[:200],
            } for d in rows],
        ),
    ]

    for key, rpc_name, transform in searches:
        try:
            response = client.rpc(rpc_name, {"query": query, "match_count": max_results}).execute()
            context[key] = transform(response.data or [])
        except Exception as exc:
            context["errors"].append(f"{rpc_name}: {exc}")

    return context


# ──────────────────────────────────────────────
# 시스템 프롬프트 — [정밀 작업 필요] 사용자가 직접 튜닝
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 한국 금융법령 전문 AI 어시스턴트 'FinLaw GPT'입니다.

역할:
- 금융법령, 조문, 판례, 해석례에 대한 질문에 정확하게 답변합니다.
- 반드시 제공된 컨텍스트(검색 결과)를 근거로 답변하세요.
- 컨텍스트에 없는 내용은 "해당 정보를 찾지 못했습니다"라고 답하세요.
- 법조문을 인용할 때는 법령명과 조문 번호를 명시하세요.

답변 형식:
1. 핵심 답변 (2-3문장)
2. 근거 법조문 또는 판례 (있는 경우)
3. 실무 참고사항 (있는 경우)

주의:
- 법률 자문이 아닌 정보 제공 목적임을 명시하세요.
- 최신 개정 사항을 반영하되, 데이터 기준일을 언급하세요.
"""


def ask(question: str) -> dict:
    """질문 → 검색 → LLM 답변"""
    # 1. 검색
    try:
        context = search_context(question)
    except Exception as exc:
        context = {"laws": [], "articles": [], "precedents": [], "interpretations": [], "errors": [str(exc)]}

    # 컨텍스트 텍스트 조합
    ctx_parts = []
    if context["laws"]:
        ctx_parts.append("## 관련 법령")
        for l in context["laws"]:
            ctx_parts.append(f"- {l['name']} ({l['ministry']}, {l['revision_type']})")
            if l["amendment_reason"]:
                ctx_parts.append(f"  개정이유: {l['amendment_reason']}")

    if context["articles"]:
        ctx_parts.append("\n## 관련 조문")
        for a in context["articles"]:
            ctx_parts.append(f"- {a['article_title']}: {a['content']}")

    if context["precedents"]:
        ctx_parts.append("\n## 관련 판례")
        for p in context["precedents"]:
            ctx_parts.append(f"- [{p['court']} {p['decision_date']}] {p['case_name']}")
            if p["summary"]:
                ctx_parts.append(f"  요지: {p['summary']}")

    if context["interpretations"]:
        ctx_parts.append("\n## 관련 해석례")
        for i in context["interpretations"]:
            ctx_parts.append(f"- {i['title']}")
            if i["summary"]:
                ctx_parts.append(f"  요지: {i['summary']}")

    if context.get("errors"):
        ctx_parts.append("\n## 검색 시스템 상태")
        for err in context["errors"]:
            ctx_parts.append(f"- {err}")

    ctx_text = "\n".join(ctx_parts) if ctx_parts else "검색 결과 없음"

    if not LLM_API_KEY:
        return {
            "answer": "LLM_API_KEY가 설정되지 않아 답변을 생성할 수 없습니다.",
            "context": context,
            "sources": _source_counts(context),
        }

    # 2. LLM 호출
    user_message = f"""다음 검색 결과를 참고하여 질문에 답변하세요.

{ctx_text}

질문: {question}"""

    try:
        r = requests.post(
            LLM_API_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "options": {"num_ctx": 32768},
            },
            timeout=60,
        )
        if r.status_code != 200:
            return {
                "answer": f"LLM 호출 실패: HTTP {r.status_code}",
                "context": context,
                "sources": _source_counts(context),
            }

        data = r.json()
        answer = data["choices"][0]["message"]["content"]

    except Exception as e:
        return {
            "answer": f"LLM 호출 에러: {e}",
            "context": context,
            "sources": _source_counts(context),
        }

    return {
        "answer": answer,
        "context": context,
        "sources": _source_counts(context),
    }


def main():
    if len(sys.argv) < 2:
        print("사용법: python -m briefingroom.finlaw_gpt '질문'")
        return
    question = " ".join(sys.argv[1:])
    print(f"\n질문: {question}\n")
    print("검색 중...")
    result = ask(question)
    print(f"\n{'='*50}")
    print(result["answer"])
    print(f"\n{'='*50}")
    src = result.get("sources", {})
    if src:
        print(f"참조: 법령 {src.get('laws',0)}건, 조문 {src.get('articles',0)}건, "
              f"판례 {src.get('precedents',0)}건, 해석례 {src.get('interpretations',0)}건")


if __name__ == "__main__":
    main()
