"""Supabase 테이블 생성 + finance_law.db 데이터 업로드

실행: python -m briefingroom.supabase_setup
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from supabase import create_client

from briefingroom.config import BASE_DIR

DB_PATH = BASE_DIR / "finance_law.db"

# .env.supabase에서 읽기
_env_path = BASE_DIR / ".env.supabase"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# SQL로 테이블 생성 (Supabase SQL Editor에서 실행하거나 REST API로)
CREATE_TABLES_SQL = """
-- 법령
create table if not exists laws (
  law_id text primary key,
  law_mst text,
  name text not null,
  name_abbr text,
  law_type text,
  ministry text,
  category text,
  promulgation_date text,
  enforcement_date text,
  revision_type text,
  detail_link text,
  article_count integer default 0,
  amendment_reason text
);

-- 조문
create table if not exists articles (
  id serial primary key,
  law_id text references laws(law_id),
  article_no text,
  article_title text,
  content text,
  full_text text
);

-- 판례
create table if not exists precedents (
  prec_id text primary key,
  case_name text,
  case_number text,
  court text,
  decision_date text,
  decision_type text,
  summary text,
  detail_link text,
  related_law text
);

-- 해석례
create table if not exists interpretations (
  interp_id text primary key,
  title text,
  decision_date text,
  decision_type text,
  summary text,
  detail_link text,
  related_law text
);

-- 행정규칙
create table if not exists admin_rules (
  rule_id text primary key,
  name text,
  rule_type text,
  ministry text,
  promulgation_date text,
  detail_link text
);

-- 입법예고
create table if not exists leg_notices (
  notice_id text primary key,
  title text not null,
  department text,
  law_type text,
  period_start text,
  period_end text,
  days integer,
  opinion_count integer default 0,
  detail_link text,
  crawled_at text
);

-- RAG용 벡터 임베딩 (향후 사용)
create table if not exists law_embeddings (
  id serial primary key,
  source_type text not null,
  source_id text not null,
  chunk_text text not null,
  embedding vector(1536),
  metadata jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_law_embeddings_embedding
  on law_embeddings using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);
"""


def create_tables():
    """Supabase REST API로 SQL 실행"""
    import requests
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    # Supabase SQL은 REST API의 rpc 또는 대시보드에서 실행
    # postgrest로는 DDL 실행 불가 → 사용자에게 SQL 제공
    print("=" * 50)
    print("아래 SQL을 Supabase SQL Editor에서 실행하세요:")
    print("=" * 50)
    print(CREATE_TABLES_SQL)
    return CREATE_TABLES_SQL


def upload_laws(client):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM laws").fetchall()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "law_id": r["law_id"],
            "law_mst": r["law_mst"],
            "name": r["name"],
            "name_abbr": r["name_abbr"],
            "law_type": r["law_type"],
            "ministry": r["ministry"],
            "category": r["category"],
            "promulgation_date": r["promulgation_date"],
            "enforcement_date": r["enforcement_date"],
            "revision_type": r["revision_type"],
            "detail_link": r["detail_link"],
            "article_count": r["article_count"],
            "amendment_reason": r["amendment_reason"] if "amendment_reason" in r.keys() else "",
        })

    # 배치 upsert (50건씩)
    for i in range(0, len(data), 50):
        batch = data[i:i+50]
        client.table("laws").upsert(batch).execute()
    print(f"[upload] laws: {len(data)}건")


def upload_articles(client):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM articles").fetchall()
    conn.close()

    data = []
    for r in rows:
        d = dict(r)
        # serial id는 Supabase에서 자동 생성되므로 제거
        d.pop("id", None)
        data.append(d)

    for i in range(0, len(data), 100):
        batch = data[i:i+100]
        client.table("articles").insert(batch).execute()
        if (i // 100) % 10 == 0:
            print(f"  articles: {i+len(batch)}/{len(data)}")
    print(f"[upload] articles: {len(data)}건")


def upload_precedents(client):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM precedents").fetchall()
    conn.close()

    data = []
    for r in rows:
        d = dict(r)
        d.pop("cached_at", None)
        data.append(d)

    for i in range(0, len(data), 50):
        batch = data[i:i+50]
        client.table("precedents").upsert(batch).execute()
    print(f"[upload] precedents: {len(data)}건")


def upload_interpretations(client):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM interpretations").fetchall()
    conn.close()

    data = []
    for r in rows:
        d = dict(r)
        d.pop("cached_at", None)
        # interp_id가 없으면 생성
        if "interp_id" not in d:
            d["interp_id"] = d.get("id", str(hash(d.get("title", ""))))
        d.pop("id", None)
        data.append(d)

    for i in range(0, len(data), 50):
        batch = data[i:i+50]
        client.table("interpretations").upsert(batch).execute()
    print(f"[upload] interpretations: {len(data)}건")


def upload_admin_rules(client):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM admin_rules").fetchall()
    conn.close()

    data = []
    for r in rows:
        d = dict(r)
        d.pop("cached_at", None)
        if "rule_id" not in d:
            d["rule_id"] = d.get("id", str(hash(d.get("name", ""))))
        d.pop("id", None)
        data.append(d)

    for i in range(0, len(data), 50):
        batch = data[i:i+50]
        client.table("admin_rules").upsert(batch).execute()
    print(f"[upload] admin_rules: {len(data)}건")


def upload_leg_notices(client):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM leg_notices").fetchall()
    conn.close()

    data = [dict(r) for r in rows]
    if data:
        client.table("leg_notices").upsert(data).execute()
    print(f"[upload] leg_notices: {len(data)}건")


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("SUPABASE_URL, SUPABASE_SERVICE_KEY 환경변수를 설정하세요")
        return

    # Step 1: SQL 출력
    sql = create_tables()

    input("\nSQL을 Supabase SQL Editor에서 실행한 후 Enter를 누르세요...")

    # Step 2: 데이터 업로드
    print("\n데이터 업로드 시작...")
    client = get_client()

    upload_laws(client)
    upload_precedents(client)
    upload_interpretations(client)
    upload_admin_rules(client)
    upload_leg_notices(client)

    # articles는 양이 많아 마지막에
    print("\narticles 업로드 중 (3,893건, 시간 소요)...")
    upload_articles(client)

    print("\n완료!")


if __name__ == "__main__":
    main()
