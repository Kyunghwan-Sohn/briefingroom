"""데이터/AI 규제 법령 수집 스크립트

법제처 Open API를 통해 개인정보보호법, AI기본법, 데이터3법 등
데이터/인공지능 관련 법령을 finance_law.db에 추가합니다.

실행: python -m briefingroom.expand_data_ai
"""
from __future__ import annotations

import json
import sqlite3
import time

import requests

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"
LAW_OC = "sony0125"
API_BASE = "https://www.law.go.kr/DRF"

# 데이터/AI 관련 법령 목록
DATA_AI_LAWS = [
    # 개인정보/데이터
    ("개인정보 보호법", "데이터"),
    ("개인정보 보호법 시행령", "데이터"),
    ("신용정보의 이용 및 보호에 관한 법률", "데이터"),
    ("정보통신망 이용촉진 및 정보보호 등에 관한 법률", "데이터"),
    ("위치정보의 보호 및 이용 등에 관한 법률", "데이터"),
    ("전자서명법", "데이터"),
    ("데이터 산업진흥 및 이용촉진에 관한 기본법", "데이터"),
    # 인공지능
    ("인공지능 산업 육성 및 신뢰 확보에 관한 법률", "인공지능"),
    ("지능정보화 기본법", "인공지능"),
    ("소프트웨어 진흥법", "인공지능"),
    ("소프트웨어산업 진흥법", "인공지능"),
    # 클라우드/디지털
    ("클라우드컴퓨팅 발전 및 이용자 보호에 관한 법률", "디지털"),
    ("전자정부법", "디지털"),
    ("전자문서 및 전자거래 기본법", "디지털"),
    ("정보보호 산업의 진흥에 관한 법률", "디지털"),
    # 통신/플랫폼
    ("전기통신사업법", "디지털"),
    ("전기통신기본법", "디지털"),
    ("온라인 플랫폼 이용자 보호에 관한 법률", "디지털"),
]

sess = requests.Session()
sess.headers.update({"User-Agent": "govbrief.kr/1.0"})


def search_law(name: str) -> dict | None:
    """법제처 API로 법령 검색"""
    try:
        r = sess.get(
            f"{API_BASE}/lawSearch.do",
            params={"OC": LAW_OC, "target": "law", "type": "JSON", "query": name, "display": 5},
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
    """법제처 API로 법령 상세 가져오기"""
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
        hang_raw = jo.get("항", {})
        if isinstance(hang_raw, list):
            hang_list = []
            for h in hang_raw:
                if isinstance(h, dict):
                    hang_list.append(h.get("항내용", ""))
                elif isinstance(h, str):
                    hang_list.append(h)
        elif isinstance(hang_raw, dict):
            hang_list = hang_raw.get("항내용", [])
            if isinstance(hang_list, str):
                hang_list = [hang_list]
            elif isinstance(hang_list, dict):
                hang_list = [hang_list.get("항내용", "")]
        else:
            hang_list = []
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
    if not DB_PATH.exists():
        print(f"[data-ai] {DB_PATH} 없음 - 스킵")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    # categories 컬럼 확인
    cols = {r[1] for r in conn.execute("PRAGMA table_info(laws)").fetchall()}
    if "categories" not in cols:
        conn.execute("ALTER TABLE laws ADD COLUMN categories TEXT DEFAULT ''")
        conn.commit()

    existing = {r[0] for r in conn.execute("SELECT name FROM laws").fetchall()}
    print(f"[data-ai] 기존 법령 {len(existing)}건, 추가 대상 {len(DATA_AI_LAWS)}건")

    added_laws = 0
    added_articles = 0

    for name, sub_category in DATA_AI_LAWS:
        if name in existing:
            # 이미 있으면 categories만 업데이트
            conn.execute(
                "UPDATE laws SET categories = CASE "
                "WHEN categories = '' OR categories IS NULL THEN ? "
                "WHEN categories NOT LIKE '%데이터AI%' THEN categories || ',데이터AI' "
                "ELSE categories END WHERE name = ?",
                ("데이터AI", name),
            )
            conn.commit()
            print(f"  [UPDATE] {name} -> 카테고리에 데이터AI 추가")
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

        amendment = get_amendment_reason(detail)
        articles = parse_articles(detail)
        law_id = info.get("law_id", info["mst"])

        conn.execute(
            "INSERT OR IGNORE INTO laws (law_id, law_mst, name, law_type, ministry, category, categories, "
            "promulgation_date, enforcement_date, article_count, amendment_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                law_id, info["mst"], name, info["law_type"], info["ministry"],
                sub_category, "데이터AI",
                info["promulgation_date"], info["enforcement_date"],
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
        print(f"  [OK] {name}: 조문 {len(articles)}건 (분류: {sub_category})")
        time.sleep(1)

    # 최종 통계
    total = conn.execute("SELECT COUNT(*) FROM laws WHERE categories LIKE '%데이터AI%'").fetchone()[0]
    total_articles = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE law_id IN (SELECT law_id FROM laws WHERE categories LIKE '%데이터AI%')"
    ).fetchone()[0]
    conn.close()

    print(f"\n[data-ai] 완료: 신규 법령 +{added_laws}건, 신규 조문 +{added_articles}건")
    print(f"[data-ai] 데이터/AI 법령 총 {total}건, 조문 총 {total_articles}건")


if __name__ == "__main__":
    run()
