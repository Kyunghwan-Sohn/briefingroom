"""브리핑룸 SQLite DB — 보도자료 전체 이력 관리

테이블: articles
  - date, source, title, url, category, finance_sub
  - summary, keywords
  - pdf_count, hwp_count, file_status (성공/실패/없음)
  - llm_status (성공/실패/한도초과/텍스트없음)
  - wp_post_id, wp_status (성공/실패/중복)
  - created_at, updated_at
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from briefingroom.config import BASE_DIR, CAT_MAP, FINANCE_SUB_MAP

DB_PATH = BASE_DIR / "briefingroom.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """테이블 생성 (없으면)"""
    conn = _conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT,
        category TEXT,
        finance_sub TEXT,
        summary TEXT,
        keywords TEXT,
        pdf_count INTEGER DEFAULT 0,
        hwp_count INTEGER DEFAULT 0,
        file_status TEXT DEFAULT 'none',
        text_length INTEGER DEFAULT 0,
        llm_status TEXT DEFAULT 'pending',
        wp_post_id INTEGER,
        wp_status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(date, source, title)
    );

    CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date);
    CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
    CREATE INDEX IF NOT EXISTS idx_articles_llm ON articles(llm_status);
    CREATE INDEX IF NOT EXISTS idx_articles_wp ON articles(wp_status);
    """)
    conn.commit()
    conn.close()


def upsert_article(item: dict, llm_status: str = "pending", wp_post_id: int = None, wp_status: str = "pending"):
    """보도자료 삽입 또는 업데이트"""
    conn = _conn()
    summary_text = ""
    keywords = ""
    if item.get("summary") and not item["summary"].startswith("["):
        for line in item["summary"].split("\n"):
            if line.startswith("요약:"):
                summary_text = line.replace("요약:", "").strip()
            elif line.startswith("키워드:"):
                keywords = line.replace("키워드:", "").strip()
        if not summary_text:
            summary_text = item["summary"]

    conn.execute("""
    INSERT INTO articles (date, source, title, url, category, finance_sub,
                          summary, keywords, pdf_count, hwp_count, file_status,
                          text_length, llm_status, wp_post_id, wp_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date, source, title) DO UPDATE SET
        summary = COALESCE(NULLIF(excluded.summary, ''), summary),
        keywords = COALESCE(NULLIF(excluded.keywords, ''), keywords),
        llm_status = CASE WHEN excluded.llm_status != 'pending' THEN excluded.llm_status ELSE llm_status END,
        wp_post_id = COALESCE(excluded.wp_post_id, wp_post_id),
        wp_status = CASE WHEN excluded.wp_status != 'pending' THEN excluded.wp_status ELSE wp_status END,
        updated_at = datetime('now','localtime')
    """, (
        item.get("date", ""),
        item.get("source", ""),
        item.get("title", "").strip(),
        item.get("url", ""),
        CAT_MAP.get(item.get("source", ""), ""),
        FINANCE_SUB_MAP.get(item.get("source", ""), ""),
        summary_text,
        keywords,
        len(item.get("pdfs", [])),
        len(item.get("hwps", [])),
        "ok" if item.get("text") else ("no_file" if not item.get("pdfs") and not item.get("hwps") else "failed"),
        len(item.get("text", "")),
        llm_status,
        wp_post_id,
        wp_status,
    ))
    conn.commit()
    conn.close()


def bulk_upsert(items: list[dict]):
    """여러 건 일괄 삽입"""
    for item in items:
        llm_status = "pending"
        if item.get("summary"):
            if item["summary"].startswith("["):
                llm_status = "failed"
            else:
                llm_status = "ok"
        upsert_article(item, llm_status=llm_status)


def update_wp_status(date_str: str, title: str, source: str, wp_post_id: int, wp_status: str):
    """WP 포스팅 결과 업데이트"""
    conn = _conn()
    conn.execute("""
    UPDATE articles SET wp_post_id=?, wp_status=?, updated_at=datetime('now','localtime')
    WHERE date=? AND title=? AND source=?
    """, (wp_post_id, wp_status, date_str, title.strip(), source))
    conn.commit()
    conn.close()


def get_stats(date_str: str = None) -> dict:
    """통계 조회"""
    conn = _conn()
    where = f"WHERE date='{date_str}'" if date_str else ""

    total = conn.execute(f"SELECT COUNT(*) FROM articles {where}").fetchone()[0]
    by_source = conn.execute(f"SELECT source, COUNT(*) cnt FROM articles {where} GROUP BY source ORDER BY cnt DESC").fetchall()
    llm_ok = conn.execute(f"SELECT COUNT(*) FROM articles {where} AND llm_status='ok'".replace("AND", "WHERE" if not where else "AND")).fetchone()[0]
    llm_fail = conn.execute(f"SELECT COUNT(*) FROM articles {where} AND llm_status='failed'".replace("AND", "WHERE" if not where else "AND")).fetchone()[0]
    wp_ok = conn.execute(f"SELECT COUNT(*) FROM articles {where} AND wp_status='ok'".replace("AND", "WHERE" if not where else "AND")).fetchone()[0]

    conn.close()
    return {
        "total": total,
        "by_source": [(r["source"], r["cnt"]) for r in by_source],
        "llm_ok": llm_ok,
        "llm_fail": llm_fail,
        "wp_ok": wp_ok,
    }


def print_dashboard(date_str: str = None):
    """대시보드 출력"""
    stats = get_stats(date_str)
    label = date_str or "전체"
    print(f"\n{'═' * 60}")
    print(f"  브리핑룸 DB 대시보드 | {label}")
    print(f"{'═' * 60}")
    print(f"  총 기사: {stats['total']}건")
    print(f"  LLM 요약: ✅ {stats['llm_ok']} | ❌ {stats['llm_fail']} | ⏳ {stats['total'] - stats['llm_ok'] - stats['llm_fail']}")
    print(f"  WP 포스팅: ✅ {stats['wp_ok']} | ⏳ {stats['total'] - stats['wp_ok']}")
    print(f"{'─' * 60}")
    print(f"  {'부처':<20} {'건수':>5}")
    print(f"  {'─'*20} {'─'*5}")
    for source, cnt in stats["by_source"][:20]:
        print(f"  {source:<20} {cnt:>5}건")
    if len(stats["by_source"]) > 20:
        print(f"  ... 외 {len(stats['by_source']) - 20}개 기관")
    print(f"{'═' * 60}")


# 초기화
init_db()
