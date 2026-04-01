"""상세 페이지 생성기

1. 보도자료 상세 브리핑: texts/ 원문 → LLM 상세 분석 → articles/{date}/{slug}/detail.html
2. 금융법령 상세: finance_law.db → finlaw/detail/{law_mst}/index.html

실행: python -m briefingroom.detail_gen
"""
from __future__ import annotations

import html as html_mod
import json
import os
import re
import sqlite3
import time
from datetime import date
from pathlib import Path

import requests

from briefingroom.config import BASE_DIR, DATA_DIR

DB_PATH = BASE_DIR / "finance_law.db"
TEXTS_DIR = BASE_DIR / "texts"
ARTICLES_DIR = BASE_DIR / "articles"
FINLAW_DIR = BASE_DIR / "finlaw"

# LLM 설정
_env = BASE_DIR / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://abcllm-api.brut.bot/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5:35b")

# CSS 공통
_CSS = """
:root{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--t);font-family:var(--sans);max-width:960px;margin:0 auto;padding:58px 0 0}
.hdr{position:fixed;top:0;left:0;right:0;z-index:50;max-width:960px;margin:0 auto;background:#f5f5f5;border-bottom:3px solid var(--a);height:54px;display:flex;align-items:center;padding:0 20px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.logo{font-family:var(--serif);font-size:19px;font-weight:700;color:var(--t);text-decoration:none;margin-right:16px;white-space:nowrap}
.hnav{display:flex;gap:0;align-items:center;flex:1;min-width:0}
.hnav a{font-size:14px;font-weight:600;color:var(--m);text-decoration:none;padding:6px 12px;border-radius:5px;white-space:nowrap}
.hnav a.on{color:var(--a);background:var(--al);font-weight:700}
.bell{color:var(--m);text-decoration:none;font-size:14px;font-weight:600;margin-left:auto;flex-shrink:0}
.wrap{padding:24px 20px 80px}
.back{color:var(--m);text-decoration:none;font-size:13px;display:inline-block;margin-bottom:16px}
h1{font-family:var(--serif);font-size:24px;font-weight:700;margin-bottom:12px;line-height:1.4}
.meta{font-size:12px;color:var(--m);margin-bottom:20px;display:flex;gap:16px;flex-wrap:wrap}
.section{background:var(--s);border:1px solid var(--b);border-radius:12px;padding:20px;margin-bottom:16px}
.section h2{font-family:var(--serif);font-size:16px;font-weight:700;margin-bottom:10px;color:var(--a)}
.section p,.section li{font-size:14px;color:var(--t2);line-height:1.8}
.section ul,.section ol{margin:8px 0 8px 20px}
.kw{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}
.kw span{font-size:11px;color:var(--a);background:var(--al);border:1px solid var(--ab);padding:3px 10px;border-radius:12px;font-weight:600}
.footer{padding:20px 24px;text-align:center;font-size:10px;color:var(--m)}
.footer a{color:var(--t);text-decoration:none;font-weight:600}
@media(max-width:768px){body{padding-top:52px}.hdr{height:50px;padding:0 14px}.logo{font-size:17px}.hnav a{font-size:11px;padding:5px 8px}.wrap{padding:20px 16px 80px}h1{font-size:20px}}
"""

_HEADER = """<header class="hdr">
  <a class="logo" href="/">브리핑룸</a>
  <nav class="hnav">
    <a href="/">정책 AI 요약</a>
    <a href="/finlaw/">금융법령 AI 모니터링</a>
  </nav>
  <a class="bell" href="https://t.me/govbrief" target="_blank">알림</a>
</header>"""

_FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">"""


# ──────────────────────────────────────────────
# [정밀 작업 필요] 상세 분석 프롬프트
# ──────────────────────────────────────────────
DETAIL_ANALYSIS_PROMPT = """당신은 Bloomberg/Reuters 수준의 정책 인텔리전스 애널리스트다.
정부 보도자료 원문(붙임 PDF/HWP 포함)을 읽고, 금융·정책 전문가가 30초 내에 의사결정에 필요한 정보를 파악할 수 있는 상세 브리핑을 작성하라.

## 출력 규칙

마크다운으로 출력한다. 섹션 구분은 ###을 사용한다.

### 핵심 요약
- 2~3문장. 반드시 핵심 숫자(%, 금액, 건수)와 날짜를 포함한다.
- 첫 문장은 "누가, 무엇을, 언제"를 담는다.
- 반복 금지. 각 문장이 서로 다른 정보를 전달해야 한다.

### 왜 중요한가
- 정확히 1문장. 이 정책이 산업·시장·국민에게 미치는 실질적 파급력을 전달한다.
- "~할 것으로 보인다", "~에 기여할 전망" 같은 관료체 금지. 직접적으로 쓴다.

### 주요 내용
- 핵심 사항만 불릿(-)으로 3~5개. 절대 6개를 넘지 않는다.
- 숫자가 원문에 있으면 반드시 포함한다.
- 각 불릿은 1~2문장으로 완결한다. 나열식 금지.

### 시행 일정
- 핵심 날짜만 기재한다. 연월일까지만(시·분 불필요).
- 날짜가 1개뿐이면 불릿 없이 한 줄로 쓴다.
- 원문에 구체적 일정이 없으면 이 섹션 자체를 생략한다.

### 관련 법령
- 원문에 법률·시행령·고시 등이 명시된 경우에만 기재한다.
- 원문에 법령 언급이 없으면 이 섹션 자체를 생략한다.

## 작성 원칙

1. 원문에 없는 내용을 추가하거나 추측하지 않는다.
2. 원문에 해당 정보가 없는 섹션은 통째로 생략한다. "언급되지 않음", "해당 없음", "확인되지 않음" 따위를 절대 쓰지 않는다.
3. 전문 용어는 본문 안에서 괄호로 인라인 설명한다. 별도 용어 섹션을 만들지 않는다.
4. 감성적·수사적 표현을 배제한다. "획기적", "대대적", "적극 추진", "만전을 기한다" 등 관료체·홍보체 표현을 사용하지 않는다.
5. 숫자 표기: 천 단위 쉼표, %는 숫자 바로 뒤에 붙인다. 금액은 억/조 단위를 쓴다.
6. 날짜 표기: YYYY.MM.DD 또는 M월 D일 형식으로 통일한다.
7. "참고사항" 같은 잡동사니 섹션을 만들지 않는다. 중요한 부가 정보는 주요 내용 불릿에 통합한다.
8. 출력 전체 길이를 간결하게 유지한다. 원문이 짧으면 브리핑도 짧아야 한다."""


def _llm_call(text: str, prompt: str = DETAIL_ANALYSIS_PROMPT) -> str:
    """LLM 상세 분석 호출"""
    if not LLM_API_KEY:
        return ""
    try:
        r = requests.post(
            LLM_API_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": prompt},
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
        print(f"  LLM 에러: {e}")
    return ""


def _md_to_html(md: str) -> str:
    """간단한 마크다운 → HTML 변환"""
    lines = md.split("\n")
    html_parts = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            if in_list:
                html_parts.append("</ol>")
                in_list = False
            html_parts.append(f'<h2>{html_mod.escape(stripped[4:])}</h2>')
        elif re.match(r"^\d+\.\s", stripped):
            if not in_list:
                html_parts.append("<ol>")
                in_list = True
            content = re.sub(r"^\d+\.\s*", "", stripped)
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            html_parts.append(f"<li>{content}</li>")
        elif stripped.startswith("- "):
            content = stripped[2:]
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            html_parts.append(f"<p>- {content}</p>")
        elif stripped:
            if in_list:
                html_parts.append("</ol>")
                in_list = False
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", stripped)
            html_parts.append(f"<p>{content}</p>")
    if in_list:
        html_parts.append("</ol>")
    return "\n".join(html_parts)


# ──────────────────────────────────────────────
# 보도자료 상세 브리핑 생성
# ──────────────────────────────────────────────
def generate_article_details(target_date: str = "", max_items: int = 20):
    """보도자료 상세 브리핑 HTML 생성

    texts/ 폴더의 원문 텍스트를 LLM으로 분석하여
    articles/{date}/{slug}/detail.html 생성
    """
    # 대상 JSON 로드
    if not target_date:
        target_date = date.today().isoformat()

    json_path = DATA_DIR / f"{target_date}.json"
    if not json_path.exists():
        json_path = DATA_DIR / "latest.json"

    if not json_path.exists():
        print("[detail_gen] JSON 파일 없음")
        return 0

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", data) if isinstance(data, dict) else data
    generated = 0

    for idx, item in enumerate(items[:max_items]):
        slug = item.get("slug") or f"{idx:03d}"
        item_date = item.get("date", target_date)
        detail_dir = ARTICLES_DIR / item_date / slug
        detail_path = detail_dir / "detail.html"

        # 이미 생성됨
        if detail_path.exists():
            continue

        # 텍스트 파일 찾기
        source = re.sub(r"[^\w가-힣]", "", item.get("source", ""))[:4]
        safe_title = re.sub(r"[^\w가-힣]", "_", item.get("title", ""))[:30]
        txt_name = f"{item_date}_{source}_{safe_title}.txt"
        txt_path = TEXTS_DIR / txt_name

        raw_text = ""
        if txt_path.exists():
            raw_text = txt_path.read_text(encoding="utf-8")

        if not raw_text or len(raw_text) < 100:
            continue

        print(f"  [{slug}] {item.get('title', '')[:50]}")

        # LLM 상세 분석
        analysis = _llm_call(raw_text)
        if not analysis:
            continue

        analysis_html = _md_to_html(analysis)

        # 키워드
        kw_html = ""
        keywords = item.get("keywords", [])
        if keywords:
            kw_html = '<div class="kw">' + "".join(f"<span>#{html_mod.escape(k)}</span>" for k in keywords) + "</div>"

        # HTML 생성
        page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_mod.escape(item.get('title',''))} - 상세 브리핑 - 브리핑룸</title>
{_FONTS}
<style>{_CSS}</style>
</head>
<body>
{_HEADER}
<div class="wrap">
<a class="back" href="/">← 브리핑룸</a>
<h1>{html_mod.escape(item.get('title',''))}</h1>
<div class="meta">
  <span>{html_mod.escape(item.get('source',''))}</span>
  <span>{item_date}</span>
  <span>영향도: {html_mod.escape(item.get('impact','중'))}</span>
</div>
{kw_html}
<div class="section">
{analysis_html}
</div>
<div style="margin-top:16px">
  <a href="{html_mod.escape(item.get('url',''), quote=True)}" target="_blank" style="font-size:13px;color:var(--a);text-decoration:none;font-weight:600">원문 보도자료 →</a>
</div>
</div>
<div class="footer"><a href="/">정책 AI 요약</a> · <a href="/finlaw/">금융법령 AI 모니터링</a><br>govbrief.kr</div>
</body>
</html>"""

        detail_dir.mkdir(parents=True, exist_ok=True)
        detail_path.write_text(page, encoding="utf-8")
        generated += 1
        print(f"    → detail.html 생성 ({len(analysis)}자)")
        time.sleep(1)

    print(f"[detail_gen] 보도자료 상세 {generated}건 생성")
    return generated


# ──────────────────────────────────────────────
# 금융법령 상세 페이지 생성
# ──────────────────────────────────────────────
def generate_law_details():
    """finance_law.db의 최근 변경 법령별 상세 페이지 생성"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 최근 변경 법령
    rows = conn.execute(
        "SELECT law_id, law_mst, name, name_abbr, law_type, ministry, "
        "promulgation_date, enforcement_date, revision_type, amendment_reason, detail_link "
        "FROM laws WHERE promulgation_date >= '20250101' ORDER BY promulgation_date DESC"
    ).fetchall()

    detail_dir = FINLAW_DIR / "detail"
    detail_dir.mkdir(parents=True, exist_ok=True)
    generated = 0

    for r in rows:
        mst = r["law_mst"]
        if not mst:
            continue

        out_dir = detail_dir / mst
        out_path = out_dir / "index.html"
        if out_path.exists():
            continue

        # 관련 조문 가져오기
        articles = conn.execute(
            "SELECT article_no, article_title, article_content FROM articles WHERE law_id = ? LIMIT 20",
            (r["law_id"],),
        ).fetchall()

        # 관련 판례
        precs = conn.execute(
            "SELECT case_name, court, decision_date, summary FROM precedents "
            "WHERE related_law LIKE ? LIMIT 5",
            (f"%{r['name']}%",),
        ).fetchall()

        name = html_mod.escape(r["name"])
        abbr = html_mod.escape(r["name_abbr"] or "")
        ministry = html_mod.escape(r["ministry"] or "")
        prom_date = r["promulgation_date"] or ""
        if len(prom_date) == 8:
            prom_date = f"{prom_date[:4]}.{prom_date[4:6]}.{prom_date[6:]}"
        enf_date = r["enforcement_date"] or ""
        if len(enf_date) == 8:
            enf_date = f"{enf_date[:4]}.{enf_date[4:6]}.{enf_date[6:]}"
        rev_type = html_mod.escape(r["revision_type"] or "")
        reason = html_mod.escape(r["amendment_reason"] or "")

        # 조문 HTML
        articles_html = ""
        if articles:
            items_html = []
            for a in articles:
                content = html_mod.escape((a["article_content"] or "")[:300])
                items_html.append(f"""<div style="margin-bottom:12px;padding:12px;background:var(--bg);border-radius:8px">
  <div style="font-weight:600;margin-bottom:4px">제{a['article_no']}조 {html_mod.escape(a['article_title'] or '')}</div>
  <div style="font-size:13px;color:var(--t2);line-height:1.7">{content}</div>
</div>""")
            articles_html = f"""<div class="section">
  <h2>주요 조문 ({len(articles)}건)</h2>
  {"".join(items_html)}
</div>"""

        # 판례 HTML
        precs_html = ""
        if precs:
            p_items = []
            for p in precs:
                summary = html_mod.escape((p["summary"] or "")[:200])
                p_items.append(f"""<div style="margin-bottom:10px;padding:12px;background:var(--bg);border-radius:8px">
  <div style="font-weight:600;font-size:13px">{html_mod.escape(p['case_name'])}</div>
  <div style="font-size:11px;color:var(--m);margin:4px 0">{html_mod.escape(p['court'] or '')} {p['decision_date'] or ''}</div>
  <div style="font-size:12px;color:var(--t2);line-height:1.6">{summary}</div>
</div>""")
            precs_html = f"""<div class="section">
  <h2>관련 판례 ({len(precs)}건)</h2>
  {"".join(p_items)}
</div>"""

        page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} - 브리핑룸</title>
{_FONTS}
<style>{_CSS}</style>
</head>
<body>
{_HEADER}
<div class="wrap">
<a class="back" href="/finlaw/">← 금융법령 AI 모니터링</a>
<h1>{name}</h1>
<div class="meta">
  <span>{abbr}</span>
  <span>{ministry}</span>
  <span>{rev_type}</span>
  <span>공포 {prom_date}</span>
  <span>시행 {enf_date}</span>
</div>

<div class="section">
  <h2>개정 이유</h2>
  <p>{reason if reason else '개정 이유 정보가 없습니다.'}</p>
</div>

{articles_html}
{precs_html}

<div style="margin-top:16px">
  <a href="https://www.law.go.kr{html_mod.escape(r['detail_link'] or '', quote=True)}" target="_blank" style="font-size:13px;color:var(--a);text-decoration:none;font-weight:600">법제처 원문 →</a>
</div>
</div>
<div class="footer"><a href="/">정책 AI 요약</a> · <a href="/finlaw/">금융법령 AI 모니터링</a><br>govbrief.kr</div>
</body>
</html>"""

        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page, encoding="utf-8")
        generated += 1

    conn.close()
    print(f"[detail_gen] 금융법령 상세 {generated}건 생성")
    return generated


def main():
    print("=" * 50)
    print("상세 페이지 생성 시작")
    print("=" * 50)
    generate_law_details()
    generate_article_details()
    print("완료")


if __name__ == "__main__":
    main()
