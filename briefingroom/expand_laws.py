"""생활법령 확장 스크립트

법제처 Open API를 통해 주택임대차보호법, 민법 등 생활밀접 법령을
finance_law.db에 추가하고 Supabase에 업로드합니다.

실행: python -m briefingroom.expand_laws
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"
LAW_OC = "sony0125"
API_BASE = "https://www.law.go.kr/DRF"

# 추가할 생활법령 목록 (법령명 기준)
EXPAND_LAWS = [
    "주택임대차보호법",
    "주택임대차보호법 시행령",
    "상가건물 임대차보호법",
    "상가건물 임대차보호법 시행령",
    "민법",
    "소비자기본법",
    "전자상거래 등에서의 소비자보호에 관한 법률",
    "개인정보 보호법",
    "개인정보 보호법 시행령",
    "근로기준법",
    "근로기준법 시행령",
    "최저임금법",
    "국민건강보험법",
    "국민연금법",
    "고용보험법",
    "산업재해보상보험법",
    "공인중개사법",
    "공인중개사법 시행령",
    "부동산 거래신고 등에 관한 법률",
    "주택법",
    "주택법 시행령",
    "건축법",
    "국세기본법",
    "소득세법",
    "부가가치세법",
    "상속세 및 증여세법",
    "종합부동산세법",
    "지방세법",
    "채무자 회생 및 파산에 관한 법률",
    "민사집행법",
    "형법",
    "형사소송법",
    "도로교통법",
    "식품위생법",
    "의료법",
    "약사법",
    "저작권법",
    "특허법",
    "상표법",
    "공정거래법",
    "하도급거래 공정화에 관한 법률",
]

sess = requests.Session()
sess.headers.update({"User-Agent": "govbrief.kr/1.0"})


def search_law(name: str) -> dict | None:
    """법제처 API로 법령 검색하여 MST(일련번호) 가져오기"""
    try:
        r = sess.get(
            f"{API_BASE}/lawSearch.do",
            params={
                "OC": LAW_OC,
                "target": "law",
                "type": "JSON",
                "query": name,
                "display": 5,
            },
            timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        items = data.get("LawSearch", {}).get("law", [])
        if isinstance(items, dict):
            items = [items]
        for item in items:
            if item.get("법령명한글", "") == name:
                return {
                    "mst": str(item.get("법령일련번호", "")),
                    "name": name,
                    "law_id": str(item.get("법령ID", item.get("법령일련번호", ""))),
                    "law_type": item.get("법령구분", ""),
                    "ministry": item.get("소관부처명", ""),
                    "promulgation_date": item.get("공포일자", ""),
                    "enforcement_date": item.get("시행일자", ""),
                }
    except Exception as e:
        print(f"  [ERR] search {name}: {e}")
    return None


def fetch_law_detail(mst: str) -> dict:
    """법제처 API로 법령 상세 (조문 포함) 가져오기"""
    try:
        r = sess.get(
            f"{API_BASE}/lawService.do",
            params={"OC": LAW_OC, "target": "law", "MST": mst, "type": "JSON"},
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  [ERR] detail MST={mst}: {e}")
    return {}


def parse_articles(law_data: dict) -> list[dict]:
    """법령 JSON에서 조문 추출"""
    articles = []
    jo_list = law_data.get("법령", {}).get("조문", {}).get("조문단위", [])
    if isinstance(jo_list, dict):
        jo_list = [jo_list]
    for jo in jo_list:
        no = jo.get("조문번호", "")
        title = jo.get("조문제목", "")
        content = jo.get("조문내용", "")
        # 항 내용 합치기
        hang_list = jo.get("항", {}).get("항내용", [])
        if isinstance(hang_list, str):
            hang_list = [hang_list]
        elif isinstance(hang_list, dict):
            hang_list = [hang_list.get("항내용", "")]
        paragraphs = []
        if isinstance(hang_list, list):
            for h in hang_list:
                if isinstance(h, dict):
                    paragraphs.append(h.get("항내용", ""))
                elif isinstance(h, str):
                    paragraphs.append(h)
        full_content = content
        if paragraphs:
            full_content += "\n" + "\n".join(paragraphs)
        articles.append({
            "article_no": str(no).strip(),
            "article_title": str(title).strip(),
            "article_content": full_content.strip(),
            "paragraphs_json": json.dumps(paragraphs, ensure_ascii=False) if paragraphs else "",
        })
    return articles


def get_amendment_reason(law_data: dict) -> str:
    """개정이유 추출"""
    amend = law_data.get("법령", {}).get("개정문", {})
    raw = amend.get("개정문내용", "")
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, list):
                parts.extend(str(x) for x in item if x)
            elif isinstance(item, str):
                parts.append(item)
        raw = " ".join(parts)
    return str(raw)[:500] if raw else ""


def run():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    existing = {r[0] for r in conn.execute("SELECT name FROM laws").fetchall()}
    print(f"[expand] 기존 법령 {len(existing)}건, 추가 대상 {len(EXPAND_LAWS)}건")

    added_laws = 0
    added_articles = 0

    for name in EXPAND_LAWS:
        if name in existing:
            print(f"  [SKIP] {name} (이미 존재)")
            continue

        print(f"  [SEARCH] {name}...")
        info = search_law(name)
        if not info or not info["mst"]:
            print(f"  [NOT FOUND] {name}")
            time.sleep(0.5)
            continue

        time.sleep(0.5)
        print(f"  [FETCH] {name} (MST={info['mst']})...")
        detail = fetch_law_detail(info["mst"])
        if not detail:
            print(f"  [FAIL] {name} 상세 조회 실패")
            time.sleep(0.5)
            continue

        # 카테고리 결정
        category = "생활법령"
        if "임대차" in name or "주택" in name or "건축" in name or "부동산" in name or "중개사" in name:
            category = "부동산"
        elif "세법" in name or "세기본" in name or "종합부동산세" in name:
            category = "세법"
        elif "근로" in name or "최저임금" in name or "고용" in name or "산업재해" in name:
            category = "노동"
        elif "건강보험" in name or "연금" in name or "의료" in name or "약사" in name:
            category = "보건복지"
        elif "소비자" in name or "전자상거래" in name or "공정거래" in name or "하도급" in name:
            category = "소비자"
        elif "형법" in name or "형사소송" in name or "도로교통" in name:
            category = "형사"
        elif "민법" in name or "민사집행" in name or "채무자" in name:
            category = "민사"
        elif "저작권" in name or "특허" in name or "상표" in name:
            category = "지식재산"
        elif "개인정보" in name:
            category = "개인정보"
        elif "식품" in name:
            category = "식품안전"

        amendment = get_amendment_reason(detail)
        articles = parse_articles(detail)

        # law_id 결정
        law_id = info.get("law_id", info["mst"])

        conn.execute(
            "INSERT OR IGNORE INTO laws (law_id, law_mst, name, law_type, ministry, category, "
            "promulgation_date, enforcement_date, article_count, amendment_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                law_id, info["mst"], name, info["law_type"], info["ministry"],
                category, info["promulgation_date"], info["enforcement_date"],
                len(articles), amendment,
            ),
        )
        added_laws += 1

        for art in articles:
            conn.execute(
                "INSERT INTO articles (law_id, article_no, article_title, article_content, paragraphs_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (law_id, art["article_no"], art["article_title"],
                 art["article_content"], art["paragraphs_json"]),
            )
            added_articles += 1

        conn.commit()
        print(f"  [OK] {name}: 조문 {len(articles)}건")
        time.sleep(1)

    conn.close()
    print(f"\n[expand] 완료: 법령 +{added_laws}건, 조문 +{added_articles}건")
    print(f"[expand] 총 법령: {len(existing) + added_laws}건")


if __name__ == "__main__":
    run()
