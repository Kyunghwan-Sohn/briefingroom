# govbrief.kr Global Expansion Technical Architecture

> 작성일: 2026-03-31
> 대상: 현재 한국 정부 보도자료 자동화 시스템 → 미국/일본/EU 확장
> 현재 규모: 27개 기관, 일 50~100건 크롤링, SQLite + GitHub Pages

---

## 목차

1. [현황 분석 및 확장 방향](#1-현황-분석-및-확장-방향)
2. [멀티 국가 크롤러 아키텍처](#2-멀티-국가-크롤러-아키텍처)
3. [다국어 LLM 요약 전략](#3-다국어-llm-요약-전략)
4. [인프라 확장 로드맵](#4-인프라-확장-로드맵)
5. [API 서비스화 설계](#5-api-서비스화-설계)
6. [데이터 파이프라인 재설계](#6-데이터-파이프라인-재설계)
7. [구현 로드맵 및 우선순위](#7-구현-로드맵-및-우선순위)

---

## 1. 현황 분석 및 확장 방향

### 1.1 현재 아키텍처 강점

```
현재 구조:
GitHub Actions (cron) → Python 크롤러 → LLM 요약 → SQLite → 정적 HTML + 텔레그램
```

| 구성요소 | 현재 | 평가 |
|----------|------|------|
| 크롤러 | 27개 부처별 Python 모듈 | 잘 구조화된 플러그인 패턴 (common.py 기반) |
| LLM | qwen3.5:35b 자체 호스팅 | 비용 효율적, 한국어 특화 |
| DB | SQLite (briefingroom.db) | 단일 서버 환경에 적합 |
| 배포 | GitHub Pages 정적 사이트 | 무료, 빠른 CDN |
| 알림 | 텔레그램 봇 | 즉시성 확보 |
| CI/CD | GitHub Actions (cron) | 자동화 완성도 높음 |

### 1.2 확장 시 한계점

| 한계 | 구체적 문제 | 영향도 |
|------|-------------|--------|
| SQLite 동시성 | 다국가 크롤러 병렬 실행 시 write lock | 높음 |
| GitHub Actions 시간 | 월 2,000분 무료 → 4국가면 월 8,000분 필요 | 높음 |
| 단일 프로세스 | app.py의 순차 실행 → 확장 시 timeout | 높음 |
| 프록시 단일 지점 | 한국 프록시 1개 → 국가별 필요 | 중간 |
| LLM 단일 모델 | 다국어 처리 시 품질 저하 가능 | 중간 |

### 1.3 확장 원칙

```
1. 점진적 확장: 한국 안정성 유지하면서 미국부터 추가
2. 플러그인 패턴 유지: 현재 crawlers/ 구조를 국가 단위로 확대
3. 인프라 전환 최소화: 필요한 부분만 교체 (SQLite → PostgreSQL 등)
4. 비용 효율: 클라우드 비용 최소화, 자체 호스팅 LLM 유지
```

---

## 2. 멀티 국가 크롤러 아키텍처

### 2.1 디렉토리 구조 설계

```
briefingroom/
  crawlers/
    __init__.py           # CRAWLERS 레지스트리 (기존 유지)
    common.py             # 공통 유틸 (기존 유지)
    base.py               # NEW: 추상 크롤러 베이스 클래스
    registry.py           # NEW: 국가별 크롤러 자동 등록

    kr/                   # 한국 (기존 크롤러 이동)
      __init__.py
      fsc.py
      moef.py
      koreakr.py
      finance.py
      president.py
      ...

    us/                   # 미국
      __init__.py
      whitehouse.py
      congress.py
      regulations.py
      federalregister.py
      sec.py
      fed.py

    jp/                   # 일본
      __init__.py
      kantei.py           # 총리관저
      egov.py             # e-Gov
      mof_jp.py           # 재무성
      meti.py             # 경제산업성

    eu/                   # EU
      __init__.py
      eurlex.py           # EUR-Lex
      europa.py           # europa.eu
      ecb.py              # 유럽중앙은행

    common/               # 국가 공통 유틸
      __init__.py
      rss_crawler.py      # RSS 기반 범용 크롤러
      api_crawler.py      # REST API 기반 범용 크롤러
      selenium_crawler.py # Playwright/Selenium 기반
```

### 2.2 추상 크롤러 베이스 클래스

```python
# briefingroom/crawlers/base.py

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class CrawlResult:
    """국가 무관 통일 데이터 구조"""
    source: str                    # 기관명 (현지어)
    source_en: str                 # 기관명 (영어)
    title: str                     # 원문 제목
    title_en: str = ""             # 영어 제목 (번역)
    url: str = ""
    date: str = ""                 # YYYY-MM-DD
    country: str = ""              # ISO 3166-1 alpha-2 (KR, US, JP, EU)
    language: str = ""             # ISO 639-1 (ko, en, ja, de, fr)
    pdfs: list[str] = field(default_factory=list)
    hwps: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    text: str = ""
    body_text: str = ""
    summary: str = ""
    category: str = ""             # 통합 카테고리
    metadata: dict = field(default_factory=dict)  # 국가별 추가 데이터


class BaseCrawler(ABC):
    """모든 국가별 크롤러의 베이스 클래스"""

    country: str = ""              # ISO 3166-1 alpha-2
    language: str = ""             # 기본 언어
    name: str = ""                 # 크롤러 표시명
    base_url: str = ""
    requires_proxy: bool = False
    requires_playwright: bool = False

    @abstractmethod
    def crawl(self, target: date) -> list[CrawlResult]:
        """해당 날짜의 보도자료를 크롤링한다."""
        ...

    def health_check(self) -> bool:
        """크롤러 상태 확인 (사이트 접근 가능 여부)"""
        try:
            from briefingroom.crawlers.common import new_session
            s = new_session()
            r = s.get(self.base_url, timeout=10)
            return r.status_code < 400
        except Exception:
            return False

    def to_legacy_item(self, result: CrawlResult) -> dict:
        """기존 make_item 호환 딕셔너리로 변환"""
        return {
            "source": result.source,
            "source_en": result.source_en,
            "title": result.title,
            "title_en": result.title_en,
            "url": result.url,
            "date": result.date,
            "country": result.country,
            "language": result.language,
            "pdfs": result.pdfs,
            "hwps": result.hwps,
            "files": result.files,
            "text": result.text,
            "body_text": result.body_text,
            "summary": result.summary,
            "category": result.category,
            "metadata": result.metadata,
        }
```

### 2.3 국가별 크롤러 구현 전략

#### 미국 (US)

| 소스 | URL | 방식 | 특이사항 |
|------|-----|------|----------|
| White House | whitehouse.gov/briefing-room | RSS/API | 구조화 잘 되어 있음 |
| Federal Register | federalregister.gov/api/v1 | REST API | 공식 API 제공, JSON 응답 |
| Congress.gov | congress.gov/bill | API | Congress API Key 필요 (무료) |
| Regulations.gov | api.regulations.gov | REST API | API Key 필요, rate limit 1000/hr |
| SEC | sec.gov/cgi-bin/browse-edgar | EDGAR API | 구조화된 filing 데이터 |
| Federal Reserve | federalreserve.gov/feeds | RSS | 표준 RSS 피드 |

```python
# briefingroom/crawlers/us/federalregister.py

class FederalRegisterCrawler(BaseCrawler):
    country = "US"
    language = "en"
    name = "Federal Register"
    base_url = "https://www.federalregister.gov"
    requires_proxy = False
    requires_playwright = False

    API_BASE = "https://www.federalregister.gov/api/v1"

    def crawl(self, target: date) -> list[CrawlResult]:
        """Federal Register API - 일별 연방관보 수집"""
        results = []
        url = f"{self.API_BASE}/documents.json"
        params = {
            "conditions[publication_date][is]": target.isoformat(),
            "per_page": 100,
            "fields[]": [
                "title", "abstract", "document_number",
                "html_url", "pdf_url", "type",
                "agencies", "publication_date"
            ],
        }
        # API 호출 + 페이지네이션 처리
        # ...
        return results
```

#### 일본 (JP)

| 소스 | URL | 방식 | 특이사항 |
|------|-----|------|----------|
| 총리관저 | kantei.go.jp | HTML 크롤링 | 보도자료 페이지 구조 단순 |
| e-Gov | e-gov.go.jp | API | 법령 API 제공 |
| 재무성 | mof.go.jp | HTML 크롤링 | RSS 일부 제공 |
| 경산성 (METI) | meti.go.jp | HTML 크롤링 | 보도자료 잘 정리됨 |
| 금융청 (FSA) | fsa.go.jp | HTML 크롤링 | 영문 페이지 병행 |

```
특이사항:
- 일본 정부 사이트는 한국보다 구조화 수준이 높음
- 영문 페이지가 대부분 존재 → 영문 크롤링 우선 검토
- e-Gov API로 법령/규정 검색 가능
- 날짜 형식: 2026年3月31日 또는 R8.3.31 (레이와 연호)
```

#### EU

| 소스 | URL | 방식 | 특이사항 |
|------|-----|------|----------|
| EUR-Lex | eur-lex.europa.eu | SPARQL/API | CELLAR 데이터베이스, 다국어 |
| Europa | europa.eu/newsroom | RSS | 뉴스룸 RSS |
| ECB | ecb.europa.eu | RSS/API | 구조화된 데이터 |
| European Commission | ec.europa.eu | HTML/RSS | 정책 분야별 피드 |

```
특이사항:
- EUR-Lex CELLAR API: SPARQL 엔드포인트 제공, 24개 언어
- 공용어가 다수 → 영어 우선, 불어/독어 보조
- 법령 체계: Regulations, Directives, Decisions 구분 필요
```

### 2.4 크롤러 레지스트리

```python
# briefingroom/crawlers/registry.py

from typing import Dict, List, Tuple
from briefingroom.crawlers.base import BaseCrawler

# 국가별 크롤러 레지스트리
_registry: Dict[str, List[Tuple[str, BaseCrawler]]] = {}


def register(country: str, name: str, crawler: BaseCrawler):
    """크롤러 등록"""
    if country not in _registry:
        _registry[country] = []
    _registry[country].append((name, crawler))


def get_crawlers(country: str = None) -> Dict[str, List[Tuple[str, BaseCrawler]]]:
    """등록된 크롤러 조회"""
    if country:
        return {country: _registry.get(country, [])}
    return dict(_registry)


def get_all_crawlers() -> List[Tuple[str, str, BaseCrawler]]:
    """전체 크롤러를 (국가, 이름, 크롤러) 튜플 리스트로 반환"""
    result = []
    for country, crawlers in _registry.items():
        for name, crawler in crawlers:
            result.append((country, name, crawler))
    return result
```

### 2.5 마이그레이션 전략 (기존 한국 크롤러)

```
Phase 1: 기존 코드 유지 + 래퍼 추가 (하위 호환)
- 기존 crawlers/*.py는 그대로 유지
- crawlers/kr/__init__.py에서 기존 크롤러를 import
- BaseCrawler 래퍼로 감싸서 레지스트리에 등록

Phase 2: 점진적 마이그레이션
- 신규 크롤러부터 BaseCrawler 직접 구현
- 기존 크롤러는 안정성 확인 후 순차 변환

코드 예시:
```

```python
# briefingroom/crawlers/kr/__init__.py

from briefingroom.crawlers.base import BaseCrawler, CrawlResult
from briefingroom.crawlers.registry import register
from briefingroom.crawlers.fsc import crawl_fsc  # 기존 크롤러


class LegacyWrapper(BaseCrawler):
    """기존 함수형 크롤러를 BaseCrawler로 래핑"""
    def __init__(self, name, name_en, legacy_fn):
        self.name = name
        self.source_en = name_en
        self.country = "KR"
        self.language = "ko"
        self._fn = legacy_fn

    def crawl(self, target):
        items = self._fn(target)
        results = []
        for item in items:
            r = CrawlResult(
                source=item["source"],
                source_en=self.source_en,
                title=item["title"],
                url=item["url"],
                date=item["date"],
                country="KR",
                language="ko",
                pdfs=item.get("pdfs", []),
                hwps=item.get("hwps", []),
                text=item.get("text", ""),
                body_text=item.get("body_text", ""),
            )
            results.append(r)
        return results


# 기존 크롤러 등록
register("KR", "금융위원회", LegacyWrapper("금융위원회", "Financial Services Commission", crawl_fsc))
# ... 나머지 27개
```

---

## 3. 다국어 LLM 요약 전략

### 3.1 모델 선택 매트릭스

| 방식 | 장점 | 단점 | 비용 (1일 기준) |
|------|------|------|-----------------|
| A: 자체 호스팅 다국어 모델 (Qwen2.5-72B) | 비용 고정, 다국어 지원 | GPU 비용, 일/영/불 품질 편차 | ~$50/월 (A6000 1대) |
| B: 언어별 특화 모델 분리 | 언어별 최적 품질 | 모델 관리 복잡 | 모델 수 x $50 |
| C: 다국어 모델 + 영어 번역 파이프라인 | 일관된 영어 출력 | 이중 처리, 지연 | ~$80/월 |
| D: Claude/GPT API (다국어) | 최고 품질, 관리 불필요 | 종량 비용, 의존성 | ~$200-500/월 |

### 3.2 권장안: C안 (다국어 모델 + 영어 번역 파이프라인)

```
선택 근거:
1. 현재 qwen3.5:35b 자체 호스팅 인프라 활용 가능
2. 원문 언어 요약 → 품질 보장
3. 영어 번역 → 글로벌 사용자 접근성
4. API 비용 없이 규모 확장 가능
```

```
파이프라인:
원문 (ko/en/ja/fr/de)
  → 언어 감지 (langdetect)
  → 원문 언어로 요약 (Qwen 72B 또는 국가별 모델)
  → 영어 번역 (요약 결과만, 짧으므로 저비용)
  → 저장: summary_original + summary_en
```

### 3.3 구현 설계

```python
# briefingroom/llm.py 확장

import langdetect

# 국가별 시스템 프롬프트
SYSTEM_PROMPTS = {
    "ko": SYSTEM_PROMPT,  # 기존 한국어 프롬프트
    "en": """You are a policy analyst specializing in government affairs.
Given a press release, respond ONLY in this format:

Summary: (3 sentences. Core policy / Key figures & timeline / Target & impact)
Keywords: keyword1, keyword2, keyword3, keyword4, keyword5
Impact: High or Medium or Low

Impact criteria (judge purely by content impact, regardless of issuing agency):
- High: New legislation, large budget (billions+), affects majority of citizens,
        new system creation/abolition, interest rate/tax/fee changes
- Medium: Existing system amendments, mid-scale budget, sector-specific impact,
          international agreements, important statistics
- Low: Personnel changes, ceremonies, job postings, simple PR""",
    "ja": """...""",  # 일본어 프롬프트
}


def detect_language(text: str) -> str:
    """텍스트 언어 감지"""
    try:
        return langdetect.detect(text[:500])
    except Exception:
        return "en"  # 감지 실패 시 영어 기본값


def summarize_multilingual(item: dict) -> dict:
    """다국어 요약 + 영어 번역"""
    text = item.get("text", "")
    lang = item.get("language", "") or detect_language(text)
    country = item.get("country", "KR")

    # 1단계: 원문 언어로 요약
    system_prompt = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["en"])
    original_summary = _call_llm(item, system_prompt)

    # 2단계: 영어가 아닌 경우 영어 번역
    if lang != "en":
        en_summary = _translate_to_english(original_summary)
    else:
        en_summary = original_summary

    return {
        "summary": original_summary,
        "summary_en": en_summary,
        "language": lang,
    }


def _translate_to_english(text: str) -> str:
    """요약문을 영어로 번역 (짧은 텍스트이므로 비용 최소)"""
    prompt = f"Translate the following government policy summary to English. Keep the same format (Summary/Keywords/Impact). Translate only, do not add commentary.\n\n{text}"
    return _call_llm_raw(prompt)
```

### 3.4 비용 최적화

```
전략:
1. 요약은 자체 호스팅 LLM (비용 고정)
2. 번역은 요약 결과만 (원문 대비 1/10 분량)
3. 영어 원문은 번역 스킵
4. 캐싱: 동일 문서 재요약 방지 (DB 체크)

예상 비용:
- 자체 호스팅: 월 $50-100 (현재와 동일한 서버 활용)
- 4개국 일 200건 x 30일 = 6,000건/월
- 번역 필요분: ~4,000건 (영어 제외)
- 번역당 평균 200토큰 → 월 80만 토큰 (자체 호스팅이면 추가 비용 없음)
```

---

## 4. 인프라 확장 로드맵

### 4.1 3단계 인프라 전환

```
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 1: 현재 유지 + 최소 확장 (0-3개월)                            │
│  ─────────────────────────────────────────────────────────────       │
│  - GitHub Actions 유지 (한국)                                        │
│  - 미국 크롤러만 추가 (Actions 분당 충분)                              │
│  - SQLite 유지 (국가별 DB 파일 분리)                                  │
│  - GitHub Pages 유지                                                 │
│                                                                      │
│  비용: $0 (무료 티어 범위)                                             │
├─────────────────────────────────────────────────────────────────────┤
│  Stage 2: 하이브리드 (3-6개월)                                        │
│  ─────────────────────────────────────────────────────────────       │
│  - VPS 1대 추가 (Hetzner/Oracle Cloud Free Tier)                     │
│  - PostgreSQL 전환 (VPS에 설치)                                       │
│  - GitHub Actions → 크롤러 실행                                      │
│  - VPS → LLM + DB + API 서빙                                        │
│  - Cloudflare Pages (정적 사이트)                                     │
│                                                                      │
│  비용: $20-40/월                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Stage 3: 풀 클라우드 (6-12개월, 사용자 증가 시)                       │
│  ─────────────────────────────────────────────────────────────       │
│  - AWS ECS 또는 GCP Cloud Run (크롤러 컨테이너)                       │
│  - RDS PostgreSQL (관리형 DB)                                        │
│  - CloudFront + S3 (정적 사이트)                                     │
│  - Redis (캐싱 + Rate Limiting)                                      │
│  - SQS/Cloud Tasks (작업 큐)                                         │
│                                                                      │
│  비용: $100-300/월                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 SQLite → PostgreSQL 마이그레이션

#### 마이그레이션 시점 판단 기준

```
지금 전환해야 하는 경우:
  - 동시 크롤러가 3개 이상 병렬 실행
  - API 서비스를 제공해야 할 때
  - 일 500건 이상 처리 시
  - 팀이 2명 이상 + 동시 접근 필요

아직 SQLite로 충분한 경우:
  - 크롤러가 순차 실행 (현재)
  - 정적 사이트 + 텔레그램만 서빙
  - 일 200건 이하
```

#### 스키마 확장

```sql
-- articles 테이블 확장 (PostgreSQL)
CREATE TABLE articles (
    id BIGSERIAL PRIMARY KEY,
    -- 기존 필드
    date DATE NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    category TEXT,
    finance_sub TEXT,
    summary TEXT,
    keywords TEXT[],              -- PostgreSQL 배열 타입 활용
    pdf_count INTEGER DEFAULT 0,
    hwp_count INTEGER DEFAULT 0,
    file_status TEXT DEFAULT 'none',
    text_length INTEGER DEFAULT 0,
    llm_status TEXT DEFAULT 'pending',
    wp_post_id INTEGER,
    wp_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 글로벌 확장 필드
    country CHAR(2) NOT NULL DEFAULT 'KR',  -- ISO 3166-1
    language CHAR(2) NOT NULL DEFAULT 'ko',  -- ISO 639-1
    source_en TEXT,                           -- 기관명 영어
    title_en TEXT,                            -- 제목 영어
    summary_en TEXT,                          -- 요약 영어
    impact TEXT DEFAULT 'medium',             -- high/medium/low
    metadata JSONB DEFAULT '{}',             -- 국가별 추가 데이터

    UNIQUE(date, source, title, country)
);

-- 인덱스
CREATE INDEX idx_articles_country ON articles(country);
CREATE INDEX idx_articles_country_date ON articles(country, date);
CREATE INDEX idx_articles_language ON articles(language);
CREATE INDEX idx_articles_impact ON articles(impact);
CREATE INDEX idx_articles_metadata ON articles USING GIN(metadata);

-- 전문 검색 (한국어 + 영어 + 일본어)
CREATE INDEX idx_articles_title_search ON articles
    USING GIN(to_tsvector('simple', title || ' ' || COALESCE(title_en, '')));

-- 국가 마스터
CREATE TABLE countries (
    code CHAR(2) PRIMARY KEY,
    name_ko TEXT NOT NULL,
    name_en TEXT NOT NULL,
    timezone TEXT NOT NULL,
    cron_schedule TEXT,           -- 크롤링 스케줄
    enabled BOOLEAN DEFAULT true
);

INSERT INTO countries VALUES
    ('KR', '대한민국', 'South Korea', 'Asia/Seoul', '40 2 * * 1-5', true),
    ('US', '미국', 'United States', 'America/New_York', '0 14 * * 1-5', false),
    ('JP', '일본', 'Japan', 'Asia/Tokyo', '0 3 * * 1-5', false),
    ('EU', 'EU', 'European Union', 'Europe/Brussels', '0 8 * * 1-5', false);

-- 크롤러 상태 추적
CREATE TABLE crawler_runs (
    id BIGSERIAL PRIMARY KEY,
    country CHAR(2) NOT NULL,
    crawler_name TEXT NOT NULL,
    target_date DATE NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',  -- running, success, failed
    items_count INTEGER DEFAULT 0,
    error_message TEXT,
    duration_seconds INTEGER
);
```

#### 마이그레이션 스크립트

```python
# scripts/migrate_sqlite_to_pg.py

import sqlite3
import psycopg2
from pathlib import Path

def migrate():
    """SQLite → PostgreSQL 데이터 마이그레이션"""
    sqlite_conn = sqlite3.connect("briefingroom.db")
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = psycopg2.connect(
        host="localhost", dbname="briefingroom",
        user="briefing", password="..."
    )

    cursor = sqlite_conn.execute("SELECT * FROM articles")
    rows = cursor.fetchall()

    pg_cur = pg_conn.cursor()
    for row in rows:
        pg_cur.execute("""
            INSERT INTO articles (
                date, source, title, url, category, finance_sub,
                summary, keywords, pdf_count, hwp_count, file_status,
                text_length, llm_status, wp_post_id, wp_status,
                country, language
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, string_to_array(%s, ', '), %s, %s, %s,
                %s, %s, %s, %s,
                'KR', 'ko'
            ) ON CONFLICT DO NOTHING
        """, (
            row["date"], row["source"], row["title"], row["url"],
            row["category"], row["finance_sub"],
            row["summary"], row["keywords"],
            row["pdf_count"], row["hwp_count"], row["file_status"],
            row["text_length"], row["llm_status"],
            row["wp_post_id"], row["wp_status"],
        ))

    pg_conn.commit()
    print(f"Migrated {len(rows)} articles")
```

### 4.3 CDN + 정적 사이트 전략

```
현재: GitHub Pages (govbrief.kr)
  장점: 무료, Cloudflare 연동 가능
  단점: 빌드 10분 제한, 1GB 저장 제한

확장안: Cloudflare Pages + Workers
  - 정적 사이트 빌드: Cloudflare Pages (무료 500빌드/월)
  - API 프록시: Cloudflare Workers (무료 10만 요청/일)
  - CDN: Cloudflare 글로벌 CDN (무료)
  - 도메인별 라우팅:
    govbrief.kr     → 한국어 사이트
    govbrief.kr/us  → 미국 섹션
    govbrief.kr/jp  → 일본 섹션
    govbrief.kr/eu  → EU 섹션
    api.govbrief.kr → API 서비스

비용: $0 (무료 티어로 충분)
```

### 4.4 GitHub Actions 최적화

```yaml
# .github/workflows/crawl-global.yml

name: global-crawl

on:
  schedule:
    # 한국: KST 11:40 = UTC 02:40
    - cron: '40 2 * * 1-5'
    # 미국: EST 09:00 = UTC 14:00
    - cron: '0 14 * * 1-5'
    # 일본: JST 12:00 = UTC 03:00
    - cron: '0 3 * * 1-5'
    # EU: CET 09:00 = UTC 08:00
    - cron: '0 8 * * 1-5'

jobs:
  crawl:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    strategy:
      matrix:
        country: [kr, us, jp, eu]
        exclude:
          # 시간대에 맞지 않는 조합 제외
          - country: us
          # cron 매칭 로직은 별도 step에서 처리

    steps:
      - uses: actions/checkout@v4

      - name: determine-country
        id: country
        run: |
          HOUR=$(date -u +%H)
          case $HOUR in
            02|03) echo "country=kr" >> $GITHUB_OUTPUT ;;
            14|15) echo "country=us" >> $GITHUB_OUTPUT ;;
            03|04) echo "country=jp" >> $GITHUB_OUTPUT ;;
            08|09) echo "country=eu" >> $GITHUB_OUTPUT ;;
          esac

      - name: crawl
        env:
          COUNTRY: ${{ steps.country.outputs.country }}
        run: python -m briefingroom.crawl --country $COUNTRY
```

```
실행 시간 최적화:
- 한국: ~30분 (27개 크롤러, 순차)
- 미국: ~10분 (API 기반, 빠름)
- 일본: ~15분 (HTML 크롤링, 적은 수)
- EU: ~10분 (API/RSS 기반)
- 합계: ~65분/일 → 월 ~1,300분 (무료 2,000분 이내)
```

---

## 5. API 서비스화 설계

### 5.1 API 아키텍처

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│   클라이언트   │────→│ Cloudflare    │────→│  API Server  │
│  (SDK/직접)   │     │  Workers      │     │  (FastAPI)   │
└──────────────┘     │  - Rate Limit │     │  - Auth      │
                     │  - Cache      │     │  - Query     │
                     │  - API Key    │     │  - Response  │
                     └───────────────┘     └──────┬───────┘
                                                  │
                                           ┌──────┴───────┐
                                           │  PostgreSQL  │
                                           │  + Redis     │
                                           └──────────────┘
```

### 5.2 엔드포인트 설계

```
Base URL: https://api.govbrief.kr/v1

인증:
  - API Key (헤더: X-API-Key)
  - 무료 티어: 100 req/day, 기본 필드만
  - Pro 티어: 10,000 req/day, 전체 필드 + 본문

엔드포인트:
```

| Method | Path | 설명 |
|--------|------|------|
| GET | `/articles` | 기사 목록 (페이지네이션, 필터) |
| GET | `/articles/{id}` | 기사 상세 |
| GET | `/articles/today` | 오늘의 기사 |
| GET | `/articles/search` | 전문 검색 |
| GET | `/countries` | 지원 국가 목록 |
| GET | `/countries/{code}/sources` | 국가별 소스 기관 목록 |
| GET | `/stats/daily` | 일별 통계 |
| GET | `/stats/weekly` | 주간 통계 |
| GET | `/feed/rss` | RSS 피드 |
| GET | `/feed/atom` | Atom 피드 |
| WS  | `/ws/stream` | 실시간 스트림 (Pro) |

### 5.3 요청/응답 스펙

```
GET /v1/articles?country=KR&date=2026-03-31&category=금융경제&impact=high&limit=20&offset=0

Response:
{
  "data": [
    {
      "id": 12345,
      "country": "KR",
      "language": "ko",
      "source": "금융위원회",
      "source_en": "Financial Services Commission",
      "title": "가계대출 관리 강화 방안 발표",
      "title_en": "Announcement of Household Loan Management Strengthening Plan",
      "url": "https://www.fsc.go.kr/...",
      "date": "2026-03-31",
      "category": "금융경제",
      "impact": "high",
      "summary": "금융위원회는 가계대출 총량 관리...",
      "summary_en": "The Financial Services Commission announced...",
      "keywords": ["가계대출", "금융규제", "DSR"],
      "keywords_en": ["household loans", "financial regulation", "DSR"],
      "has_full_text": true,
      "related_laws": [...],
      "published_at": "2026-03-31T09:00:00+09:00"
    }
  ],
  "meta": {
    "total": 45,
    "limit": 20,
    "offset": 0,
    "request_id": "req_abc123"
  }
}
```

### 5.4 FastAPI 서버 구현

```python
# briefingroom/api/main.py

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import date

app = FastAPI(
    title="GovBrief API",
    description="Global Government Press Release API",
    version="1.0.0",
    docs_url="/v1/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://govbrief.kr"],
    allow_methods=["GET"],
    allow_headers=["X-API-Key"],
)


@app.get("/v1/articles")
async def list_articles(
    country: Optional[str] = Query(None, regex="^[A-Z]{2}$"),
    date: Optional[date] = None,
    category: Optional[str] = None,
    impact: Optional[str] = Query(None, regex="^(high|medium|low)$"),
    source: Optional[str] = None,
    language: Optional[str] = Query(None, regex="^[a-z]{2}$"),
    q: Optional[str] = Query(None, min_length=2, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key),
):
    """기사 목록 조회"""
    # 쿼리 빌드 + 실행
    ...


@app.get("/v1/articles/today")
async def today_articles(
    country: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    """오늘의 기사 (타임존 고려)"""
    ...
```

### 5.5 API 키 관리 + 과금

```
Stage 1 (무료만):
  - API 키 발급: 이메일 인증 후 즉시 발급
  - 저장: PostgreSQL api_keys 테이블
  - Rate Limit: Cloudflare Workers에서 처리

Stage 2 (유료 추가):
  - Stripe 연동 (월 $29 Pro / $99 Enterprise)
  - 사용량 추적: Redis INCR + 일별 집계
  - 초과 시: 429 응답 + 업그레이드 안내

테이블:
```

```sql
CREATE TABLE api_keys (
    id BIGSERIAL PRIMARY KEY,
    key_hash TEXT UNIQUE NOT NULL,     -- SHA-256 해시
    email TEXT NOT NULL,
    plan TEXT DEFAULT 'free',          -- free/pro/enterprise
    daily_limit INTEGER DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE api_usage (
    id BIGSERIAL PRIMARY KEY,
    api_key_id BIGINT REFERENCES api_keys(id),
    date DATE NOT NULL,
    request_count INTEGER DEFAULT 0,
    UNIQUE(api_key_id, date)
);
```

### 5.6 SDK 설계

```python
# Python SDK: pip install govbrief

from govbrief import GovBrief

client = GovBrief(api_key="gb_...")

# 오늘의 한국 보도자료
articles = client.articles.today(country="KR")

# 특정 날짜 미국 금융 규제
articles = client.articles.list(
    country="US",
    date="2026-03-31",
    category="financial",
    impact="high",
)

# 검색
results = client.articles.search("household loan regulation")

# 실시간 스트림 (Pro)
for article in client.stream(countries=["KR", "US"]):
    print(f"[{article.country}] {article.title}")
```

```javascript
// JavaScript SDK: npm install govbrief

import { GovBrief } from 'govbrief';

const client = new GovBrief({ apiKey: 'gb_...' });

const articles = await client.articles.today({ country: 'KR' });
const results = await client.articles.search('financial regulation');
```

---

## 6. 데이터 파이프라인 재설계

### 6.1 현재 vs 목표

```
현재 (순차 단일 프로세스):
┌────────────────────────────────────────────────────────┐
│  app.py main()                                         │
│                                                        │
│  crawl_koreakr() → crawl_finance_all() → 개별크롤러   │
│       ↓                                                │
│  dedup() → verify() → fill_missing()                  │
│       ↓                                                │
│  process_item() (파일 추출)                             │
│       ↓                                                │
│  summarize() (LLM 요약) — 순차, 1.5초 딜레이           │
│       ↓                                                │
│  WordPress + 정적 사이트 + 텔레그램                      │
└────────────────────────────────────────────────────────┘

목표 (이벤트 기반 병렬):
┌────────────────────────────────────────────────────────┐
│  Scheduler (cron per country)                          │
│       ↓                                                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ KR      │  │ US      │  │ JP      │  │ EU      │  │
│  │ Crawlers│  │ Crawlers│  │ Crawlers│  │ Crawlers│  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │
│       └────────────┴────────────┴────────────┘        │
│                        ↓                               │
│              Message Queue (Redis/SQS)                │
│                        ↓                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ 파일추출  │  │ LLM요약  │  │ 번역     │             │
│  │ Worker   │  │ Worker   │  │ Worker   │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       └──────────────┴──────────────┘                  │
│                        ↓                               │
│              PostgreSQL (통합 저장)                     │
│                        ↓                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ 정적생성  │  │ 텔레그램  │  │ API갱신  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└────────────────────────────────────────────────────────┘
```

### 6.2 단계별 전환

#### Phase 1: 멀티프로세스 (현재 인프라 유지)

```python
# briefingroom/parallel.py
from concurrent.futures import ThreadPoolExecutor, as_completed
from briefingroom.crawlers.registry import get_crawlers


def crawl_country(country: str, target: date) -> list[dict]:
    """국가 단위 크롤러 병렬 실행"""
    crawlers = get_crawlers(country)
    all_items = []

    # 같은 국가 내 크롤러는 ThreadPool로 병렬 (I/O bound)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(crawler.crawl, target): name
            for name, crawler in crawlers.get(country, [])
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                items = future.result(timeout=120)
                all_items.extend(items)
                print(f"  [{name}] {len(items)}건")
            except Exception as e:
                print(f"  [{name}] 실패: {e}")

    return all_items
```

#### Phase 2: Redis Queue 기반 (VPS 추가 시)

```python
# briefingroom/queue.py
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)

QUEUE_CRAWL = "queue:crawl"
QUEUE_EXTRACT = "queue:extract"
QUEUE_SUMMARIZE = "queue:summarize"
QUEUE_TRANSLATE = "queue:translate"
QUEUE_NOTIFY = "queue:notify"


def enqueue(queue: str, item: dict):
    """작업 큐에 아이템 추가"""
    r.rpush(queue, json.dumps(item, ensure_ascii=False))


def dequeue(queue: str, timeout: int = 30) -> dict:
    """작업 큐에서 아이템 가져오기 (blocking)"""
    result = r.blpop(queue, timeout=timeout)
    if result:
        return json.loads(result[1])
    return None


# Worker 예시
def summarize_worker():
    """LLM 요약 워커 — 독립 프로세스로 실행"""
    while True:
        item = dequeue(QUEUE_SUMMARIZE)
        if not item:
            continue
        try:
            result = summarize_multilingual(item)
            item.update(result)
            enqueue(QUEUE_TRANSLATE, item)
        except Exception as e:
            print(f"[요약 실패] {e}")
            item["summary"] = f"[요약 실패] {e}"
            enqueue(QUEUE_NOTIFY, item)
```

### 6.3 모니터링 + 알림

```python
# briefingroom/monitoring.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CrawlMetrics:
    country: str
    crawler_name: str
    target_date: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    items_count: int = 0
    errors_count: int = 0
    duration_seconds: float = 0
    status: str = "running"


class Monitor:
    """크롤링 파이프라인 모니터링"""

    def __init__(self):
        self.metrics: list[CrawlMetrics] = []

    def start_crawl(self, country, name, target_date) -> CrawlMetrics:
        m = CrawlMetrics(country=country, crawler_name=name,
                         target_date=target_date, started_at=datetime.now())
        self.metrics.append(m)
        return m

    def finish_crawl(self, m: CrawlMetrics, items_count: int, errors: int = 0):
        m.finished_at = datetime.now()
        m.items_count = items_count
        m.errors_count = errors
        m.duration_seconds = (m.finished_at - m.started_at).total_seconds()
        m.status = "success" if errors == 0 else "partial"

    def report(self) -> dict:
        """전체 파이프라인 리포트"""
        return {
            "total_crawlers": len(self.metrics),
            "success": sum(1 for m in self.metrics if m.status == "success"),
            "partial": sum(1 for m in self.metrics if m.status == "partial"),
            "failed": sum(1 for m in self.metrics if m.status == "failed"),
            "total_items": sum(m.items_count for m in self.metrics),
            "total_errors": sum(m.errors_count for m in self.metrics),
            "total_duration": sum(m.duration_seconds for m in self.metrics),
            "by_country": self._group_by_country(),
        }

    def _group_by_country(self) -> dict:
        groups = {}
        for m in self.metrics:
            if m.country not in groups:
                groups[m.country] = {"items": 0, "errors": 0, "crawlers": 0}
            groups[m.country]["items"] += m.items_count
            groups[m.country]["errors"] += m.errors_count
            groups[m.country]["crawlers"] += 1
        return groups

    def alert_if_needed(self):
        """이상 감지 시 텔레그램 알림"""
        report = self.report()

        alerts = []
        if report["failed"] > 0:
            alerts.append(f"크롤러 실패: {report['failed']}개")
        if report["total_items"] == 0:
            alerts.append("수집 건수 0건 (전체 실패 의심)")
        for country, stats in report["by_country"].items():
            if stats["items"] == 0 and stats["crawlers"] > 0:
                alerts.append(f"{country}: 수집 0건")

        if alerts:
            self._send_telegram_alert("\n".join(alerts))
```

---

## 7. 구현 로드맵 및 우선순위

### 7.1 Phase 1: 미국 추가 (4주)

```
Week 1: 기반 구조
  [x] BaseCrawler 추상 클래스 작성
  [x] CrawlResult 데이터 구조 정의
  [x] 크롤러 레지스트리 구현
  [x] 기존 한국 크롤러 LegacyWrapper 적용
  [x] articles 테이블에 country, language 컬럼 추가 (SQLite ALTER)

Week 2: 미국 크롤러 구현
  [ ] Federal Register API 크롤러
  [ ] White House RSS 크롤러
  [ ] Congress.gov API 크롤러
  [ ] SEC EDGAR 크롤러
  [ ] Federal Reserve RSS 크롤러

Week 3: 다국어 LLM 확장
  [ ] 영어 시스템 프롬프트 작성 + 테스트
  [ ] 언어 감지 로직 추가
  [ ] summarize_multilingual() 구현
  [ ] 영어→한국어 번역 파이프라인 (선택적)

Week 4: 통합 + 배포
  [ ] GitHub Actions 워크플로우 확장 (미국 cron 추가)
  [ ] 정적 사이트 /us 섹션 생성
  [ ] 텔레그램 미국 브리핑 채널 (별도 또는 통합)
  [ ] 테스트 + 안정화
```

### 7.2 Phase 2: 인프라 전환 + 일본/EU (8주)

```
Week 1-2: 인프라
  [ ] VPS 설정 (Hetzner CPX31: 4vCPU, 8GB, ~$15/월)
  [ ] PostgreSQL 설치 + 스키마 생성
  [ ] SQLite → PostgreSQL 마이그레이션
  [ ] db.py 리팩터링 (SQLite/PostgreSQL 듀얼 지원)

Week 3-4: 일본 크롤러
  [ ] kantei.go.jp 크롤러
  [ ] mof.go.jp 크롤러
  [ ] meti.go.jp 크롤러
  [ ] fsa.go.jp 크롤러
  [ ] 일본어 시스템 프롬프트

Week 5-6: EU 크롤러
  [ ] Federal Register API 크롤러
  [ ] EUR-Lex CELLAR API 크롤러
  [ ] europa.eu RSS 크롤러
  [ ] ECB RSS 크롤러
  [ ] 다국어 (영/불/독) 처리

Week 7-8: 파이프라인 고도화
  [ ] Redis 큐 도입
  [ ] 크롤러 병렬 실행
  [ ] 모니터링 대시보드
  [ ] 알림 고도화
```

### 7.3 Phase 3: API 서비스화 (6주)

```
Week 1-2: API 서버
  [ ] FastAPI 프로젝트 구조
  [ ] 엔드포인트 구현
  [ ] API 키 발급/인증
  [ ] Rate Limiting

Week 3-4: 배포 + 문서
  [ ] Cloudflare Workers 프록시
  [ ] API 문서 (OpenAPI/Swagger)
  [ ] 개발자 포털 페이지

Week 5-6: SDK
  [ ] Python SDK (govbrief)
  [ ] JavaScript SDK (@govbrief/sdk)
  [ ] 샘플 코드 + 튜토리얼
```

### 7.4 비용 요약

| 항목 | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| 서버 | $0 (GitHub) | $15-40/월 (VPS) | $50-100/월 |
| DB | $0 (SQLite) | $0 (self-hosted PG) | $0 |
| LLM | $0 (자체 호스팅) | $0 | $0 |
| CDN | $0 (GitHub Pages) | $0 (Cloudflare) | $0 |
| 도메인 | 기존 | 기존 | api.govbrief.kr |
| 합계 | $0/월 | $15-40/월 | $50-100/월 |

### 7.5 리스크 매트릭스

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| 미국 사이트 IP 차단 | 낮음 | 높음 | 공식 API 우선 사용, 프록시 대비 |
| LLM 다국어 품질 저하 | 중간 | 중간 | 언어별 프롬프트 최적화, 모델 교체 대비 |
| GitHub Actions 시간 초과 | 중간 | 중간 | 국가별 워크플로우 분리, 타임아웃 최적화 |
| 해외 정부 사이트 구조 변경 | 높음 | 중간 | API 우선, 크롤러 건강 체크 자동화 |
| SQLite→PG 마이그레이션 실패 | 낮음 | 높음 | 듀얼 모드 운영, 롤백 계획 |
| 한국 서비스 안정성 저하 | 중간 | 높음 | 한국은 독립 파이프라인 유지 |

---

## 부록: 주요 의사결정 근거

### 왜 FastAPI인가?

```
현재 Python 코드베이스와 동일 언어 → 학습 비용 없음
비동기 지원 → API 동시성 처리
자동 OpenAPI 문서 생성
타입 힌트 기반 → 코드 품질 유지
```

### 왜 Cloudflare인가?

```
무료 티어가 매우 관대 (Workers: 10만 req/일, Pages: 500빌드/월)
글로벌 CDN → 각국 사용자 접근성
DDoS 보호 기본 포함
GitHub Pages 대비 빌드 유연성 높음
```

### 왜 VPS (Hetzner)인가?

```
AWS/GCP 대비 3-5배 저렴 (같은 스펙)
한국/미국/EU 데이터센터 선택 가능
PostgreSQL + Redis + LLM API 모두 한 서버에서 운영 가능
초기 비용 최소화 → 규모 확장 시 클라우드 전환
```

### 왜 Redis Queue인가 (Celery/RabbitMQ 아닌)?

```
이미 Rate Limiting용 Redis가 필요 → 추가 인프라 없음
파이프라인이 단순 (크롤링 → 요약 → 저장) → Celery 과잉
Redis Streams 활용 시 메시지 영속성도 확보
운영 복잡도 최소화 (RabbitMQ는 관리 부담)
```
