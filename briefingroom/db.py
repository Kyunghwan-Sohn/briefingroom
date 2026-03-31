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
UPSERT_SQL = """
    INSERT INTO articles (date, source, title, url, category, finance_sub,
                          summary, keywords, pdf_count, hwp_count, file_status,
                          text_length, llm_status, wp_post_id, wp_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date, source, title) DO UPDATE SET
        url = COALESCE(NULLIF(excluded.url, ''), url),
        category = COALESCE(NULLIF(excluded.category, ''), category),
        finance_sub = COALESCE(NULLIF(excluded.finance_sub, ''), finance_sub),
        summary = COALESCE(NULLIF(excluded.summary, ''), summary),
        keywords = COALESCE(NULLIF(excluded.keywords, ''), keywords),
        pdf_count = excluded.pdf_count,
        hwp_count = excluded.hwp_count,
        file_status = excluded.file_status,
        text_length = excluded.text_length,
        llm_status = CASE WHEN excluded.llm_status != 'pending' THEN excluded.llm_status ELSE llm_status END,
        wp_post_id = COALESCE(excluded.wp_post_id, wp_post_id),
        wp_status = CASE WHEN excluded.wp_status != 'pending' THEN excluded.wp_status ELSE wp_status END,
        updated_at = datetime('now','localtime')
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
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


def _summary_parts(item: dict) -> tuple[str, str]:
    from briefingroom.storage import extract_summary_parts
    raw = item.get("summary", "")
    if not raw or raw.startswith("["):
        return "", ""
    summary_text, _, _, kw_list, _ = extract_summary_parts(raw)
    keywords = ", ".join(kw_list)
    if not summary_text:
        summary_text = raw
    return summary_text, keywords


def _article_row(item: dict, llm_status: str = "pending", wp_post_id: int = None, wp_status: str = "pending") -> tuple:
    summary_text, keywords = _summary_parts(item)
    return (
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
    )


def upsert_article(item: dict, llm_status: str = "pending", wp_post_id: int = None, wp_status: str = "pending"):
    """보도자료 삽입 또는 업데이트"""
    conn = _conn()
    conn.execute(UPSERT_SQL, _article_row(item, llm_status=llm_status, wp_post_id=wp_post_id, wp_status=wp_status))
    conn.commit()
    conn.close()


def bulk_upsert(items: list[dict]):
    """여러 건 일괄 삽입"""
    rows = []
    for item in items:
        llm_status = "pending"
        if item.get("summary"):
            if item["summary"].startswith("["):
                llm_status = "failed"
            else:
                llm_status = "ok"
        rows.append(_article_row(item, llm_status=llm_status))
    if not rows:
        return
    conn = _conn()
    conn.executemany(UPSERT_SQL, rows)
    conn.commit()
    conn.close()


def update_wp_status(date_str: str, title: str, source: str, wp_post_id: int, wp_status: str):
    """WP 포스팅 결과 업데이트"""
    conn = _conn()
    conn.execute("""
    UPDATE articles SET wp_post_id=?, wp_status=?, updated_at=datetime('now','localtime')
    WHERE date=? AND title=? AND source=?
    """, (wp_post_id, wp_status, date_str, title.strip(), source))
    conn.commit()
    conn.close()


def bulk_update_wp_status(rows: list[tuple[str, str, str, int, str]]):
    """WP 포스팅 결과 일괄 업데이트"""
    if not rows:
        return
    conn = _conn()
    conn.executemany("""
    UPDATE articles SET wp_post_id=?, wp_status=?, updated_at=datetime('now','localtime')
    WHERE date=? AND title=? AND source=?
    """, [
        (wp_post_id, wp_status, date_str, title.strip(), source)
        for date_str, title, source, wp_post_id, wp_status in rows
    ])
    conn.commit()
    conn.close()


def get_stats(date_str: str = None) -> dict:
    """통계 조회"""
    conn = _conn()
    params = (date_str,) if date_str else ()
    base_where = " WHERE date=?" if date_str else ""
    status_prefix = f"{base_where} AND " if date_str else " WHERE "

    total = conn.execute(f"SELECT COUNT(*) FROM articles{base_where}", params).fetchone()[0]
    by_source = conn.execute(
        f"SELECT source, COUNT(*) cnt FROM articles{base_where} GROUP BY source ORDER BY cnt DESC",
        params,
    ).fetchall()
    llm_ok = conn.execute(
        f"SELECT COUNT(*) FROM articles{status_prefix}llm_status='ok'",
        params,
    ).fetchone()[0]
    llm_fail = conn.execute(
        f"SELECT COUNT(*) FROM articles{status_prefix}llm_status='failed'",
        params,
    ).fetchone()[0]
    wp_ok = conn.execute(
        f"SELECT COUNT(*) FROM articles{status_prefix}wp_status='ok'",
        params,
    ).fetchone()[0]

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
