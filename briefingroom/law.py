"""법제처 Open API 클라이언트 + SQLite 캐시

보도자료에서 추출된 법령명으로 법제처 API를 조회하고,
결과를 SQLite에 30일간 캐시하여 API 호출을 최소화합니다.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

from briefingroom.config import BASE_DIR

LAW_OC = "sony0125"
LAW_API_BASE = "http://www.law.go.kr/DRF"
LAW_CACHE_DB = BASE_DIR / "law_cache.db"
CACHE_DAYS = 30

_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": "govbrief.kr/1.0"})
    return _session


# ═══════════════════════════════════════════════════════════
#  SQLite 캐시
# ═══════════════════════════════════════════════════════════

def _init_cache():
    conn = sqlite3.connect(str(LAW_CACHE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS law_cache (
            law_name TEXT PRIMARY KEY,
            law_id TEXT,
            law_mst TEXT,
            law_type TEXT,
            ministry TEXT,
            promulgation_date TEXT,
            enforcement_date TEXT,
            detail_link TEXT,
            articles_json TEXT,
            cached_at TEXT,
            UNIQUE(law_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS article_law (
            article_date TEXT,
            article_title TEXT,
            law_name TEXT,
            article_ref TEXT,
            PRIMARY KEY(article_date, article_title, law_name)
        )
    """)
    conn.commit()
    conn.close()


def _get_cached(law_name: str) -> dict | None:
    """캐시에서 법령 조회 (30일 이내)"""
    conn = sqlite3.connect(str(LAW_CACHE_DB))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM law_cache WHERE law_name = ? AND cached_at > ?",
        (law_name, (datetime.now() - timedelta(days=CACHE_DAYS)).isoformat()),
    ).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["articles"] = json.loads(result.pop("articles_json", "[]"))
        return result
    return None


def _save_cache(data: dict):
    """법령 정보를 캐시에 저장"""
    conn = sqlite3.connect(str(LAW_CACHE_DB))
    conn.execute("""
        INSERT OR REPLACE INTO law_cache
        (law_name, law_id, law_mst, law_type, ministry,
         promulgation_date, enforcement_date, detail_link, articles_json, cached_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["law_name"], data.get("law_id", ""), data.get("law_mst", ""),
        data.get("law_type", ""), data.get("ministry", ""),
        data.get("promulgation_date", ""), data.get("enforcement_date", ""),
        data.get("detail_link", ""), json.dumps(data.get("articles", []), ensure_ascii=False),
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def save_article_law(article_date: str, article_title: str, law_name: str, article_ref: str = ""):
    """보도자료 ↔ 법령 연결 저장"""
    _init_cache()
    conn = sqlite3.connect(str(LAW_CACHE_DB))
    conn.execute("""
        INSERT OR IGNORE INTO article_law (article_date, article_title, law_name, article_ref)
        VALUES (?, ?, ?, ?)
    """, (article_date, article_title.strip(), law_name, article_ref))
    conn.commit()
    conn.close()


def get_laws_for_article(article_date: str, article_title: str) -> list[dict]:
    """보도자료에 연결된 법령 목록 조회"""
    _init_cache()
    conn = sqlite3.connect(str(LAW_CACHE_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT al.law_name, al.article_ref, lc.law_type, lc.ministry,
               lc.enforcement_date, lc.detail_link, lc.articles_json
        FROM article_law al
        LEFT JOIN law_cache lc ON al.law_name = lc.law_name
        WHERE al.article_date = ? AND al.article_title = ?
    """, (article_date, article_title.strip())).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d["articles"] = json.loads(d.pop("articles_json", "[]") or "[]")
        result.append(d)
    return result


# ═══════════════════════════════════════════════════════════
#  법제처 API 호출
# ═══════════════════════════════════════════════════════════

def search_law(law_name: str) -> dict | None:
    """법령 검색 → 법령일련번호(MST) 반환. 캐시 우선."""
    _init_cache()

    # 캐시 확인
    cached = _get_cached(law_name)
    if cached:
        print(f"    [법령] 캐시 히트: {law_name}")
        return cached

    # API 호출
    print(f"    [법령] API 호출: {law_name}")
    try:
        r = _get_session().get(
            f"{LAW_API_BASE}/lawSearch.do",
            params={"OC": LAW_OC, "target": "law", "type": "JSON",
                    "query": law_name, "display": 3},
            timeout=15,
        )
        if r.status_code != 200:
            print(f"    [법령] HTTP {r.status_code}")
            return None

        data = r.json()
        laws = data.get("LawSearch", {}).get("law", [])
        if isinstance(laws, dict):
            laws = [laws]
        if not laws:
            print(f"    [법령] 검색 결과 없음: {law_name}")
            return None

        # 법령명이 가장 유사한 것 선택
        best = laws[0]
        for law in laws:
            name = law.get("법령명한글", "")
            if name == law_name:
                best = law
                break

        result = {
            "law_name": best.get("법령명한글", law_name),
            "law_id": best.get("법령ID", ""),
            "law_mst": best.get("법령일련번호", ""),
            "law_type": best.get("법령구분명", ""),
            "ministry": best.get("소관부처명", ""),
            "promulgation_date": best.get("공포일자", ""),
            "enforcement_date": best.get("시행일자", ""),
            "detail_link": best.get("법령상세링크", ""),
            "articles": [],
        }

        _save_cache(result)
        time.sleep(0.5)
        return result

    except Exception as e:
        print(f"    [법령] 검색 실패: {law_name} | {e}")
        return None


def get_article_text(law_mst: str, article_no: int) -> dict | None:
    """특정 법령의 특정 조문 조회"""
    try:
        r = _get_session().get(
            f"{LAW_API_BASE}/lawService.do",
            params={"OC": LAW_OC, "target": "law", "type": "JSON",
                    "MST": law_mst},
            timeout=15,
        )
        if r.status_code != 200:
            return None

        data = r.json()
        jomun = data.get("법령", {}).get("조문", {}).get("조문단위", [])
        if isinstance(jomun, dict):
            jomun = [jomun]

        for jo in jomun:
            if str(jo.get("조문번호", "")) == str(article_no):
                # 항 파싱
                hangs = jo.get("항", [])
                if isinstance(hangs, dict):
                    hangs = [hangs]

                items = []
                for hang in hangs:
                    h_content = hang.get("항내용", "")
                    # 호 파싱
                    hos = hang.get("호", [])
                    if isinstance(hos, dict):
                        ho_list = hos.get("호단위", [])
                        if isinstance(ho_list, dict):
                            ho_list = [ho_list]
                    elif isinstance(hos, list):
                        ho_list = hos
                    else:
                        ho_list = []

                    sub_items = []
                    for ho in ho_list:
                        sub_items.append(ho.get("호내용", ""))

                    items.append({
                        "content": h_content,
                        "sub_items": sub_items,
                    })

                return {
                    "article_no": article_no,
                    "title": jo.get("조문제목", ""),
                    "content": jo.get("조문내용", ""),
                    "items": items,
                }

        return None
    except Exception as e:
        print(f"    [법령] 조문 조회 실패: MST={law_mst}, 조={article_no} | {e}")
        return None


# ═══════════════════════════════════════════════════════════
#  법령명 추출 (LLM 요약 결과에서)
# ═══════════════════════════════════════════════════════════

# 자주 등장하는 법령명 패턴
_LAW_SUFFIXES = r"(?:기본법|특별법|특례법|촉진법|지원법|관리법|보호법|규제법|처벌법|방지법|육성법|진흥법|설치법|운영법|조정법|이용법|활용법|개발법|정비법|안전법|위생법|교육법|복지법|보험법|보장법|거래법|통신법|방송법|의료법|약사법|식품법|건축법|도로법|항공법|해운법|철도법|수산업법|축산법|산림법|환경법|에너지법|전기법|소방법|경찰법|군사법|외교법|관세법|세법|예산법|회계법|조달법)"
_LAW_PATTERN = re.compile(
    r"(?:「|['\"])"
    r"([\w가-힣·\s]{2,30}(?:법|령|규칙|조례|규정))"
    r"(?:」|['\"])"
    r"(?:\s*(?:제(\d+)조(?:의(\d+))?))?|"
    r"(?<![가-힣])"
    r"((?:[\w가-힣]+\s)*[\w가-힣]*(?:보호법|기본법|특별법|특례법|촉진법|지원법|관리법|규제법|처벌법|방지법|육성법|진흥법|거래법|보험법|보장법|안전법|교육법|복지법|의료법|건축법|통신법|정보법|신용정보법|자본시장법|공정거래법|상법|민법|형법|세법|관세법|노동법|고용법|산업안전법|환경법|에너지법|전기법|소방법|도로법|항공법|해운법))"
    r"(?:\s*(?:제(\d+)조(?:의(\d+))?))?",
)


def extract_law_names(text: str) -> list[dict]:
    """텍스트에서 법령명 + 조문번호 추출"""
    results = []
    seen = set()

    for match in _LAW_PATTERN.finditer(text):
        # 괄호 매칭 (「법령명」) 또는 비괄호 매칭
        law_name = (match.group(1) or match.group(4) or "").strip()
        article_no = match.group(2) or match.group(5)
        article_sub = match.group(3) or match.group(6)

        if not law_name or len(law_name) < 3:
            continue
        # 앞에 붙은 부처명+조사 제거 (예: "금융위원회가 신용정보법" → "신용정보법")
        # 조사(가/는/의/을/를/에/과/와) + 공백 패턴으로만 분리
        m_clean = re.match(r".*?[가는의을를에과와]\s+(.+(?:법|령|규칙))$", law_name)
        if m_clean:
            law_name = m_clean.group(1)
        law_name = law_name.strip()
        if not law_name or len(law_name) < 3:
            continue
        if law_name in seen:
            continue

        seen.add(law_name)
        ref = ""
        if article_no:
            ref = f"제{article_no}조"
            if article_sub:
                ref += f"의{article_sub}"

        results.append({"law_name": law_name, "article_ref": ref})

    return results


# ═══════════════════════════════════════════════════════════
#  보도자료 처리 통합
# ═══════════════════════════════════════════════════════════

def process_law_for_item(item: dict) -> list[dict]:
    """보도자료 1건에서 법령 추출 → API 조회 → 연결 저장"""
    # 요약에서 법령명 추출 (제목은 부처명 등이 섞여 오탐 발생)
    text = item.get("summary", "")
    laws = extract_law_names(text)

    if not laws:
        return []

    results = []
    for law_info in laws[:3]:  # 최대 3개 법령
        law_name = law_info["law_name"]
        article_ref = law_info["article_ref"]

        # 법령 검색 (캐시 우선)
        law_data = search_law(law_name)
        if law_data:
            # 보도자료 ↔ 법령 연결 저장
            save_article_law(
                item.get("date", ""),
                item.get("title", ""),
                law_data["law_name"],
                article_ref,
            )
            results.append({
                "law_name": law_data["law_name"],
                "law_type": law_data.get("law_type", ""),
                "ministry": law_data.get("ministry", ""),
                "enforcement_date": law_data.get("enforcement_date", ""),
                "article_ref": article_ref,
                "detail_link": law_data.get("detail_link", ""),
            })

    return results


def process_laws_for_items(items: list[dict], max_api_calls: int = 50) -> int:
    """보도자료 리스트 전체에서 법령 연동 처리. API 호출 횟수 제한."""
    _init_cache()
    total_linked = 0
    api_calls = 0

    for item in items:
        if api_calls >= max_api_calls:
            print(f"    [법령] API 호출 한도 도달 ({max_api_calls}회) → 중단")
            break

        laws = process_law_for_item(item)
        if laws:
            item["related_laws"] = laws
            total_linked += 1
            # 캐시 미스 시에만 API 호출 카운트 (search_law 내부에서 처리)
            api_calls += sum(1 for l in laws if not _get_cached(l["law_name"]))

    print(f"    [법령] {total_linked}건 연결 완료 (API 호출 ~{api_calls}회)")
    return total_linked
