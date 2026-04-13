"""법령 조문 간 참조 관계 추출 및 인덱스 구축

모든 조문 텍스트에서 다른 조문을 참조하는 패턴을 추출하여
law_references 테이블에 저장한다.

"자본시장법 제3조" 검색 시:
1. 같은 법 하위 법령(시행령·감독규정·세칙)에서 참조하는 조문
2. 다른 법에서 「자본시장법」 제3조를 직접 참조하는 조문
3. 재귀적으로 참조 체인 추적

테이블: law_references
  - source_law_id, source_law_name, source_article_no
  - target_law_id, target_law_name, target_article_no
  - ref_type: 'down' (상위→하위), 'cross' (다른 법 참조), 'internal' (같은 법)
  - ref_text: 원문에서 추출한 참조 문구

실행: python -m briefingroom.law_references
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"

# ─── 참조 패턴 (한국 법령 표준) ───

# 다른 법 참조: 「법령명」 제N조
PAT_EXTERNAL = re.compile(
    r'「([^」]{2,40}?)」\s*제(\d+)조(?:의(\d+))?'
)

# 같은 법 상위 참조: "법 제N조", "이 법 제N조"
PAT_PARENT_LAW = re.compile(
    r'(?:이\s*)?법\s+제(\d+)조(?:의(\d+))?'
)

# 시행령 참조: "영 제N조", "같은 영 제N조", "시행령 제N조"
PAT_DECREE = re.compile(
    r'(?:같은\s*)?(?:영|시행령)\s+제(\d+)조(?:의(\d+))?'
)

# 감독규정 참조: "규정 제N조", "감독규정 제N조"
PAT_REGULATION = re.compile(
    r'(?:같은\s*)?(?:규정|감독규정)\s+제(\d+(?:-\d+)?)조'
)


def _article_no_str(no: str, sub: str | None = None) -> str:
    """조문번호 표준화: '3' → '3', ('3', '2') → '3의2'"""
    result = str(no).strip()
    if sub:
        result += f"의{sub}"
    return result


def _get_law_hierarchy(conn: sqlite3.Connection) -> dict:
    """법령 간 상하위 관계 매핑.

    법 → 시행령 → 감독규정 → 시행세칙 관계를
    법령명 패턴으로 추론.
    """
    rows = conn.execute("SELECT law_id, name, law_type FROM laws").fetchall()
    laws = {r[0]: {"name": r[1], "type": r[2]} for r in rows}
    name_to_id = {r[1]: r[0] for r in rows}

    hierarchy = {}
    for law_id, info in laws.items():
        name = info["name"]
        ltype = info["type"]

        if ltype in ("법률", "법"):
            base = name
        elif "시행령" in name:
            base = name.replace(" 시행령", "").replace("시행령", "")
        elif "시행규칙" in name:
            base = name.replace(" 시행규칙", "").replace("시행규칙", "")
        else:
            base = name

        base = base.strip()
        if base not in hierarchy:
            hierarchy[base] = {"법률": None, "시행령": None, "감독규정": [], "시행세칙": []}

        if ltype in ("법률", "법"):
            hierarchy[base]["법률"] = law_id
        elif "시행령" in name:
            hierarchy[base]["시행령"] = law_id
        elif "규정" in name or "규칙" in name:
            hierarchy[base]["감독규정"].append(law_id)

    return hierarchy


def extract_references_from_article(
    source_law_id: str,
    source_law_name: str,
    source_article_no: str,
    content: str,
    all_laws: dict[str, str],
) -> list[dict]:
    """하나의 조문에서 모든 참조 관계를 추출."""
    refs = []
    seen = set()

    def _add(target_law_name: str, target_article: str, ref_type: str, ref_text: str):
        key = (target_law_name, target_article, ref_type)
        if key in seen:
            return
        seen.add(key)
        target_law_id = all_laws.get(target_law_name, "")
        refs.append({
            "source_law_id": source_law_id,
            "source_law_name": source_law_name,
            "source_article_no": source_article_no,
            "target_law_id": target_law_id,
            "target_law_name": target_law_name,
            "target_article_no": target_article,
            "ref_type": ref_type,
            "ref_text": ref_text[:200],
        })

    # 1. 다른 법 직접 참조: 「법령명」 제N조
    for m in PAT_EXTERNAL.finditer(content):
        law_name = m.group(1).strip()
        art_no = _article_no_str(m.group(2), m.group(3))
        if law_name != source_law_name:
            _add(law_name, art_no, "cross", m.group(0))

    # 2. "법 제N조" — 상위법 참조 (시행령·감독규정에서 사용)
    for m in PAT_PARENT_LAW.finditer(content):
        art_no = _article_no_str(m.group(1), m.group(2))
        if "시행령" in source_law_name or "규정" in source_law_name or "규칙" in source_law_name:
            parent_name = (
                source_law_name
                .replace(" 시행령", "")
                .replace("시행령", "")
                .replace(" 시행규칙", "")
                .replace("시행규칙", "")
                .strip()
            )
            _add(parent_name, art_no, "up", m.group(0))

    # 3. "영 제N조" — 시행령 참조
    for m in PAT_DECREE.finditer(content):
        art_no = _article_no_str(m.group(1), m.group(2))
        decree_name = source_law_name.replace(" 시행규칙", "").replace("시행규칙", "")
        if "시행령" not in decree_name:
            parent = (
                source_law_name
                .replace(" 시행규칙", "")
                .replace("시행규칙", "")
                .strip()
            )
            decree_name = parent + " 시행령"
        _add(decree_name, art_no, "up", m.group(0))

    return refs


def build_reference_index():
    """전체 조문 스캔 → law_references 테이블 구축."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 테이블 생성
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS law_references (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_law_id TEXT,
        source_law_name TEXT,
        source_article_no TEXT,
        target_law_id TEXT,
        target_law_name TEXT,
        target_article_no TEXT,
        ref_type TEXT,
        ref_text TEXT,
        UNIQUE(source_law_id, source_article_no, target_law_name, target_article_no, ref_type)
    );
    CREATE INDEX IF NOT EXISTS idx_ref_target
        ON law_references(target_law_name, target_article_no);
    CREATE INDEX IF NOT EXISTS idx_ref_source
        ON law_references(source_law_name, source_article_no);
    """)

    # 기존 데이터 삭제 (재구축)
    conn.execute("DELETE FROM law_references")

    # 모든 법령명 → law_id 매핑
    all_laws = {
        r["name"]: r["law_id"]
        for r in conn.execute("SELECT law_id, name FROM laws").fetchall()
    }

    # 모든 조문 가져오기
    articles = conn.execute("""
        SELECT a.law_id, l.name as law_name, a.article_no, a.article_content as content
        FROM articles a
        JOIN laws l ON a.law_id = l.law_id
        WHERE a.article_content IS NOT NULL AND a.article_content != ''
    """).fetchall()

    print(f"[law_references] {len(articles)}개 조문 스캔 시작")

    total_refs = 0
    for art in articles:
        text = art["content"] or ""
        refs = extract_references_from_article(
            source_law_id=art["law_id"],
            source_law_name=art["law_name"],
            source_article_no=art["article_no"],
            content=text,
            all_laws=all_laws,
        )
        for ref in refs:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO law_references
                    (source_law_id, source_law_name, source_article_no,
                     target_law_id, target_law_name, target_article_no,
                     ref_type, ref_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        ref["source_law_id"], ref["source_law_name"], ref["source_article_no"],
                        ref["target_law_id"], ref["target_law_name"], ref["target_article_no"],
                        ref["ref_type"], ref["ref_text"],
                    ),
                )
                total_refs += 1
            except Exception:
                pass

    conn.commit()
    print(f"[law_references] 완료 — {total_refs}개 참조 관계 추출")

    # 통계
    stats = conn.execute(
        "SELECT ref_type, COUNT(*) FROM law_references GROUP BY ref_type"
    ).fetchall()
    for s in stats:
        print(f"  {s[0]}: {s[1]}건")

    conn.close()
    return total_refs


def search_references(law_name: str, article_no: str, depth: int = 3) -> dict:
    """특정 조문의 참조 관계를 재귀적으로 탐색.

    Returns:
        {
            "root": {"law_name": ..., "article_no": ..., "content": ...},
            "down": [...],    # 이 조문을 참조하는 하위 법령 조문
            "cross": [...],   # 이 조문을 참조하는 다른 법 조문
            "up": [...],      # 이 조문이 참조하는 상위 법령 조문
        }
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 원문 가져오기
    root_article = conn.execute(
        """SELECT a.content, a.full_text, a.article_title, l.name
        FROM articles a JOIN laws l ON a.law_id = l.law_id
        WHERE l.name = ? AND a.article_no = ?""",
        (law_name, article_no),
    ).fetchone()

    root = {
        "law_name": law_name,
        "article_no": article_no,
        "article_title": root_article["article_title"] if root_article else "",
        "content": (root_article["content"] or "") if root_article else "",
    }

    # 이 조문을 target으로 참조하는 모든 조문 (하위/크로스)
    referencing = conn.execute(
        """SELECT source_law_name, source_article_no, ref_type, ref_text
        FROM law_references
        WHERE target_law_name = ? AND target_article_no = ?
        ORDER BY ref_type, source_law_name""",
        (law_name, article_no),
    ).fetchall()

    # 이 조문이 source로 참조하는 모든 조문 (상위)
    referenced = conn.execute(
        """SELECT target_law_name, target_article_no, ref_type, ref_text
        FROM law_references
        WHERE source_law_name = ? AND source_article_no = ?
        ORDER BY ref_type, target_law_name""",
        (law_name, article_no),
    ).fetchall()

    result = {
        "root": root,
        "referenced_by": [dict(r) for r in referencing],
        "references_to": [dict(r) for r in referenced],
    }

    conn.close()
    return result


def run():
    print("[law_references] 참조 인덱스 구축")
    build_reference_index()


if __name__ == "__main__":
    run()
