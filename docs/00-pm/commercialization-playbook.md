# GovBrief.kr 상업화 실행 플레이북

**Product**: BriefingRoom (govbrief.kr)
**Date**: 2026-03-29
**Version**: 1.0
**Target**: 금융사 준법감시팀 B2B SaaS
**Year 1 Goal**: ARR 7,000만원 (20개사 x 월 29만원)

---

# 1. 12주 실행 로드맵

## Week 1-2: 기반 구축 (2026-03-30 ~ 04-12)

### Week 1: 사업 인프라 + 랜딩페이지

| 일자 | 액션 | 산출물 | 담당 |
|------|------|--------|------|
| Day 1 (월) | 사업자등록 신청 (홈택스 온라인) | 사업자등록증 (3~5일 소요) | 본인 |
| Day 1 (월) | govbrief.kr/pro 랜딩페이지 코딩 시작 | HTML/CSS 초안 | 본인 |
| Day 2 (화) | 랜딩페이지 카피 작성 + 디자인 완성 | 완성된 랜딩페이지 | 본인 |
| Day 3 (수) | 스티비 계정 생성 + 뉴스레터 템플릿 설정 | 발송 가능 상태 | 본인 |
| Day 3 (수) | 링크드인 프로필 최적화 (govbrief.kr 연결) | 업데이트된 프로필 | 본인 |
| Day 4 (목) | "금융 규제 모니터링 주간 리포트" 첫 호 제작 | PDF + 이메일 버전 | 본인 |
| Day 5 (금) | 랜딩페이지 배포 + 뉴스레터 구독 폼 연동 | govbrief.kr/pro 라이브 | 본인 |

**랜딩페이지 핵심 요소**:
- 히어로: "금융 규제 보도자료, AI가 5분 만에 요약합니다"
- 무료 체험 CTA: "2주 무료 체험 시작" (이메일만 입력)
- 무료 체험 시 제공: 매일 금융 규제 이메일 브리핑 + 주간 분석 리포트
- 신뢰 요소: "51개 부처 보도자료 매일 자동 수집", "금융위/금감원/한국은행 등 25개 금융기관 커버"

### Week 2: 무료 체험 시스템 + 초기 아웃리치

| 일자 | 액션 | 산출물 |
|------|------|--------|
| Day 6 (월) | 스티비에서 "금융 규제 데일리 브리핑" 자동 발송 세팅 | 자동화 워크플로 |
| Day 7 (화) | 기존 텔레그램 채널에 Pro 출시 공지 | 텔레그램 포스트 |
| Day 8 (수) | 링크드인 첫 포스트: "금융 규제 모니터링 자동화" 주제 | 링크드인 게시글 |
| Day 9 (목) | ICP 기업 리스트 20개사 확정 + 담당자 LinkedIn 탐색 | 타겟 리스트 스프레드시트 |
| Day 10 (금) | 첫 콜드 이메일 10통 발송 (증권사 5 + 자산운용사 5) | 발송 기록 |

**무료 체험 구현 방법 (Week 1-2에서는 수동)**:
- 스티비 주소록에 "무료체험" 태그로 관리
- 매일 오전 9시, 금융 카테고리 보도자료 AI 요약을 이메일로 발송
- 기존 파이프라인에서 금융 카테고리 데이터 추출하는 스크립트 추가
- 주간 리포트는 기존 weekly.py 출력물을 금융 섹션만 발췌하여 PDF 제작

---

## Week 3-4: MVP 개발 (2026-04-13 ~ 04-26)

### Week 3: FastAPI 서버 + 인증 + 키워드 알림

| 일자 | 태스크 | 상세 |
|------|--------|------|
| Day 1-2 | FastAPI 프로젝트 초기 설정 | 프로젝트 구조, DB 연결, 기본 라우트 |
| Day 3 | JWT 인증 시스템 구현 | 회원가입, 로그인, 토큰 발급/검증 |
| Day 4 | 키워드 알림 엔진 v1 | 사용자별 키워드 등록 + 매칭 로직 |
| Day 5 | 키워드 알림 이메일 발송 연동 | 매칭된 보도자료 이메일 자동 발송 |

### Week 4: 대시보드 UI + 결제 준비

| 일자 | 태스크 | 상세 |
|------|--------|------|
| Day 1-2 | Pro 대시보드 프론트엔드 | 금융 보도자료 필터, 키워드 관리, 알림 이력 |
| Day 3 | 주간 리포트 자동 생성 API | 기존 weekly.py를 API로 래핑 |
| Day 4 | Toss Payments 연동 준비 | 사업자 인증, API 키 발급, 테스트 결제 |
| Day 5 | 통합 테스트 + 베타 버전 배포 | staging 환경에서 전체 플로우 검증 |

---

## Week 5-8: 베타 고객 확보 (2026-04-27 ~ 05-24)

### Week 5-6: 집중 아웃리치

**목표**: 무료 체험 사용자 30명 확보

| 채널 | 주간 액션 | 목표 |
|------|----------|------|
| 콜드 이메일 | 20통/주 발송 (ICP 기업 준법감시팀) | 응답률 15% = 3건/주 |
| 링크드인 | 연결 요청 30건/주 + DM 10건/주 | 전환 10% = 3건/주 |
| 텔레그램 | 기존 채널 프로모션 주 1회 | 전환 5% |
| 금융 커뮤니티 | 블라인드/금융인 커뮤니티 콘텐츠 공유 | 인바운드 유도 |

**콜드 이메일 발송 타임라인**:
- Week 5: 대형 증권사 10개사 (한국투자/미래에셋/NH/삼성/메리츠/키움/신한/KB/하나/대신)
- Week 6: 자산운용사 10개사 (미래에셋/삼성/한화/KB/신한/한국투자/키움/삼성액티브/KCGI/한국투자밸류)
- Week 7: 보험사/핀테크 10개사
- Week 8: 2차 팔로업 전체

### Week 7-8: 피드백 수렴 + 제품 개선

| 액션 | 방법 | 목표 |
|------|------|------|
| 사용자 인터뷰 | 무료 체험 사용자 중 10명과 30분 통화 | 핵심 Pain Point 3가지 확인 |
| 제품 개선 | 인터뷰 기반 상위 3개 기능 개선 | NPS 8+ 달성 |
| 유료 전환 준비 | 가격 민감도 조사 (반 다이크 모델) | 최적 가격대 확정 |

---

## Week 9-12: 유료 전환 (2026-05-25 ~ 06-21)

### Week 9-10: 결제 시스템 라이브 + 유료 전환 캠페인

| 액션 | 상세 |
|------|------|
| Toss Payments 정기결제 연동 라이브 | 월 29만원 자동 결제 |
| 무료 체험 만료 알림 시퀀스 | D-7, D-3, D-1, D-day 이메일 |
| 1:1 유료 전환 미팅 | 무료 체험 중 활성 사용자 상위 10명과 화상 미팅 |
| 연간 구독 할인 제안 | 연간 결제 시 2개월 무료 (월 24만원 환산) |

### Week 11-12: 첫 유료 고객 + 운영 안정화

| 액션 | 목표 |
|------|------|
| 첫 유료 전환 | 최소 3개사 유료 전환 |
| 온보딩 프로세스 확립 | 가입 후 24시간 내 키워드 세팅 완료 가이드 |
| CS 프로세스 확립 | 이메일 기반 CS + FAQ 페이지 |
| 월간 리뷰 리포트 | 고객별 활용 현황 리포트 자동 생성 |

**12주 종료 시점 목표 KPI**:
- 무료 체험 등록: 50명
- 유료 전환: 3~5개사
- MRR: 87~145만원
- NPS: 8+

---

# 2. MVP 기술 구현 명세

## 2.1 현재 코드베이스 구조

```
briefingroom/
  app.py          # 메인 파이프라인 (크롤링 -> 요약 -> 배포)
  config.py       # 설정 (API, 부처 매핑, 카테고리)
  db.py           # SQLite DB (articles 테이블)
  llm.py          # LLM 요약 (qwen3.5:35b)
  pipeline.py     # 파일 처리 (PDF/HWP 추출)
  telegram.py     # 텔레그램 발송
  static_gen.py   # RSS + HTML 생성
  weekly.py       # 주간 리포트 (McKinsey 스타일)
  schedule.py     # 차주 정부 일정
  crawlers/       # 34개 크롤러 (korea.kr + 개별 부처 + 금융기관)
```

## 2.2 추가해야 할 모듈

```
briefingroom/
  api/                    # [신규] FastAPI 서버
    __init__.py
    main.py               # FastAPI 앱, CORS, 미들웨어
    auth.py               # JWT 인증 (회원가입/로그인/토큰)
    routes/
      articles.py         # 보도자료 조회 API
      alerts.py           # 키워드 알림 CRUD
      reports.py          # 주간 리포트 API
      billing.py          # 결제/구독 관리
      users.py            # 사용자 프로필
    middleware/
      rate_limit.py       # Rate limiting
      auth_middleware.py   # JWT 검증 미들웨어
    models/
      user.py             # 사용자 Pydantic 모델
      alert.py            # 알림 설정 모델
      subscription.py     # 구독/결제 모델
  alert_engine.py         # [신규] 키워드 매칭 엔진
  email_sender.py         # [신규] 이메일 발송 (스티비 API)
  pro_dashboard/          # [신규] 프론트엔드 (정적 HTML + Vanilla JS)
    index.html
    dashboard.html
    login.html
    static/
      app.js
      style.css
```

## 2.3 FastAPI 서버 구조

### main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="GovBrief Pro API",
    version="1.0.0",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://govbrief.kr"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트 등록
from briefingroom.api.routes import articles, alerts, reports, billing, users
app.include_router(articles.router, prefix="/api/v1/articles", tags=["articles"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```

### API 엔드포인트 명세

| Method | Path | 설명 | 인증 |
|--------|------|------|------|
| POST | `/api/v1/users/register` | 회원가입 | 불필요 |
| POST | `/api/v1/users/login` | 로그인 (JWT 발급) | 불필요 |
| GET | `/api/v1/users/me` | 내 정보 조회 | 필요 |
| PUT | `/api/v1/users/me` | 내 정보 수정 | 필요 |
| GET | `/api/v1/articles` | 보도자료 목록 (필터: 날짜, 카테고리, 키워드) | 필요 |
| GET | `/api/v1/articles/{id}` | 보도자료 상세 | 필요 |
| GET | `/api/v1/articles/search` | 전문 검색 | 필요 |
| POST | `/api/v1/alerts` | 키워드 알림 등록 | 필요 |
| GET | `/api/v1/alerts` | 내 알림 목록 | 필요 |
| PUT | `/api/v1/alerts/{id}` | 알림 수정 | 필요 |
| DELETE | `/api/v1/alerts/{id}` | 알림 삭제 | 필요 |
| GET | `/api/v1/alerts/history` | 알림 발송 이력 | 필요 |
| GET | `/api/v1/reports/weekly` | 주간 리포트 목록 | 필요 |
| GET | `/api/v1/reports/weekly/{date}` | 특정 주간 리포트 | 필요 |
| POST | `/api/v1/billing/subscribe` | 구독 시작 (Toss Payments) | 필요 |
| POST | `/api/v1/billing/cancel` | 구독 취소 | 필요 |
| GET | `/api/v1/billing/status` | 구독 상태 조회 | 필요 |
| POST | `/api/v1/billing/webhook` | Toss Payments 웹훅 | 불필요 (서명 검증) |

### 인증 흐름

```
[클라이언트] --POST /login--> [FastAPI]
                                  |
                           이메일+비밀번호 검증
                                  |
                           JWT 액세스 토큰 발급
                           (만료: 24시간)
                                  |
               <--200 {token}-----+

[클라이언트] --GET /articles--> [FastAPI]
              Authorization:        |
              Bearer {token}   JWT 검증 미들웨어
                                  |
                             유효 -> 데이터 반환
                             만료 -> 401 Unauthorized
```

## 2.4 DB 스키마 변경

### 결론: SQLite 유지 (Year 1)

**근거**:
- 현재 일 ~100건, 연간 ~36,500건 = SQLite로 충분
- 유료 고객 20개사 수준에서는 동시 접속 문제 없음
- 마이그레이션 비용 대비 효과 낮음
- WAL 모드 이미 활성화 (동시 읽기 지원)
- Year 2에서 고객 50개사 초과 시 PostgreSQL 마이그레이션 검토

### 추가 테이블

```sql
-- 사용자 테이블
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    company_name TEXT,
    company_type TEXT,  -- 'securities'|'asset_mgmt'|'insurance'|'fintech'|'other'
    department TEXT,
    name TEXT,
    phone TEXT,
    plan TEXT DEFAULT 'trial',  -- 'trial'|'pro'|'enterprise'
    trial_start TEXT,
    trial_end TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 구독/결제 테이블
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan TEXT NOT NULL,  -- 'pro_monthly'|'pro_annual'|'enterprise'
    status TEXT DEFAULT 'active',  -- 'active'|'cancelled'|'expired'|'past_due'
    toss_billing_key TEXT,  -- Toss Payments 빌링키
    toss_customer_key TEXT,
    amount INTEGER NOT NULL,  -- 월 결제 금액 (원)
    started_at TEXT,
    expires_at TEXT,
    cancelled_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 키워드 알림 테이블
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    keywords TEXT NOT NULL,  -- 쉼표 구분: "자본시장법,금융소비자보호,과징금"
    categories TEXT,  -- 필터: "금융경제,행정법제" (빈값=전체)
    sources TEXT,  -- 필터: "금융위원회,금융감독원" (빈값=전체)
    frequency TEXT DEFAULT 'realtime',  -- 'realtime'|'daily_9am'|'weekly'
    channel TEXT DEFAULT 'email',  -- 'email'|'slack'|'webhook'
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 알림 발송 이력
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL REFERENCES alerts(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    article_id INTEGER REFERENCES articles(id),
    matched_keyword TEXT,
    sent_at TEXT DEFAULT (datetime('now','localtime')),
    channel TEXT,
    status TEXT DEFAULT 'sent'  -- 'sent'|'failed'|'opened'|'clicked'
);

-- API 사용 로그 (Rate limiting + 분석용)
CREATE TABLE api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    endpoint TEXT,
    method TEXT,
    status_code INTEGER,
    response_time_ms INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_alerts_user ON alerts(user_id);
CREATE INDEX idx_alert_history_user ON alert_history(user_id);
CREATE INDEX idx_alert_history_sent ON alert_history(sent_at);
CREATE INDEX idx_api_logs_user ON api_logs(user_id);
CREATE INDEX idx_api_logs_created ON api_logs(created_at);
```

## 2.5 키워드 알림 엔진

### 알고리즘

```python
# alert_engine.py - 핵심 로직

import re
from typing import list

def match_keywords(article: dict, alert: dict) -> list[str]:
    """보도자료와 알림 키워드 매칭. 매칭된 키워드 리스트 반환."""

    matched = []
    keywords = [k.strip() for k in alert["keywords"].split(",")]

    # 검색 대상 텍스트 구성
    search_text = " ".join([
        article.get("title", ""),
        article.get("summary", ""),
        article.get("keywords", ""),
    ]).lower()

    for keyword in keywords:
        kw = keyword.lower().strip()
        if not kw:
            continue

        # 1. 정확한 문자열 매칭
        if kw in search_text:
            matched.append(keyword)
            continue

        # 2. 형태소 변형 매칭 (한국어 조사 처리)
        #    "자본시장법" -> "자본시장법을", "자본시장법에", "자본시장법의" 등
        pattern = re.compile(rf'{re.escape(kw)}[은는이가을를의에서로와과도만]?')
        if pattern.search(search_text):
            matched.append(keyword)
            continue

    # 3. 카테고리 필터 적용
    if alert.get("categories"):
        allowed_cats = [c.strip() for c in alert["categories"].split(",")]
        if article.get("category") not in allowed_cats:
            return []  # 카테고리 불일치 시 전체 무효

    # 4. 기관 필터 적용
    if alert.get("sources"):
        allowed_sources = [s.strip() for s in alert["sources"].split(",")]
        if article.get("source") not in allowed_sources:
            return []

    return matched


def run_alert_check(articles: list[dict], db_conn):
    """새 보도자료에 대해 모든 활성 알림 체크 + 발송"""

    # 모든 활성 알림 조회
    active_alerts = db_conn.execute(
        "SELECT * FROM alerts WHERE is_active = 1"
    ).fetchall()

    notifications = []  # (user_id, alert_id, article, matched_keywords)

    for article in articles:
        for alert in active_alerts:
            matched = match_keywords(article, dict(alert))
            if matched:
                notifications.append({
                    "user_id": alert["user_id"],
                    "alert_id": alert["id"],
                    "article": article,
                    "matched_keywords": matched,
                    "channel": alert["channel"],
                    "frequency": alert["frequency"],
                })

    # 빈도별 그룹핑
    realtime = [n for n in notifications if n["frequency"] == "realtime"]
    daily = [n for n in notifications if n["frequency"] == "daily_9am"]

    # 실시간 알림 즉시 발송
    for notification in realtime:
        send_alert_email(notification)

    # 일간 알림은 큐에 저장 (다음 날 오전 9시 배치 발송)
    for notification in daily:
        queue_alert(notification)

    return len(realtime), len(daily)
```

### 파이프라인 통합

기존 `app.py`의 `main()` 함수에서 LLM 요약 완료 후 알림 엔진 호출:

```python
# app.py main() 에 추가할 위치: LLM 요약 완료 후, WordPress 포스팅 전

# ── Pro 알림 발송 ───────────────────────────────────
from briefingroom.alert_engine import run_alert_check
realtime_count, daily_count = run_alert_check(all_items, db_conn)
print(f"  [Pro 알림] 실시간 {realtime_count}건, 일간 큐 {daily_count}건")
```

## 2.6 결제 연동: Toss Payments

### 선택 근거

| 항목 | Toss Payments | Stripe Korea |
|------|--------------|--------------|
| 한국 사업자 지원 | 네이티브 | 글로벌 (KR 지원) |
| 정기결제 (빌링) | 지원 | 지원 |
| 카드 수수료 | 3.3~4.3% | 3.4% |
| 세금계산서 연동 | 자동 | 수동 |
| 한국어 문서/SDK | 완벽 | 부분 |
| 설정 난이도 | 낮음 | 중간 |
| **결론** | **추천** | 글로벌 확장 시 |

### 정기결제 흐름

```
[사용자] --> govbrief.kr/pro/subscribe
              |
              v
        [Toss 결제창] --> 카드 정보 입력
              |
              v
        [Toss 서버] --> 빌링키 발급 (authKey)
              |
              v
        [GovBrief API] POST /api/v1/billing/webhook
              |
              +--> billingKey 저장
              +--> subscriptions 테이블 INSERT
              +--> 사용자 plan = 'pro'
              |
              v
        [매월 1일 배치]
              |
              +--> Toss API: POST /v1/billing/{billingKey}
              +--> 결제 성공 -> 다음 달 갱신
              +--> 결제 실패 -> 3일간 재시도, 이후 만료 처리
```

### 핵심 API 호출

```python
# billing.py - Toss Payments 정기결제

import httpx

TOSS_SECRET_KEY = "test_sk_..."  # 시크릿 키
TOSS_API_BASE = "https://api.tosspayments.com"

async def create_billing_key(auth_key: str, customer_key: str):
    """카드 등록 후 빌링키 발급"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TOSS_API_BASE}/v1/billing/authorizations/issue",
            json={
                "authKey": auth_key,
                "customerKey": customer_key,
            },
            auth=(TOSS_SECRET_KEY, ""),
        )
        return resp.json()  # {"billingKey": "...", "card": {...}}

async def charge_billing(billing_key: str, customer_key: str, amount: int, order_id: str):
    """정기결제 실행"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TOSS_API_BASE}/v1/billing/{billing_key}",
            json={
                "customerKey": customer_key,
                "amount": amount,
                "orderId": order_id,
                "orderName": "GovBrief Pro 월간 구독",
            },
            auth=(TOSS_SECRET_KEY, ""),
        )
        return resp.json()
```

### 가격 체계

| 플랜 | 월 가격 | 연간 가격 | 포함 내역 |
|------|---------|----------|----------|
| **Trial** | 무료 (14일) | - | 금융 규제 데일리 브리핑, 키워드 알림 3개 |
| **Pro** | 290,000원 | 2,900,000원 (2개월 무료) | 전체 51개 부처, 키워드 알림 무제한, 주간 리포트, API 접근 |
| **Enterprise** | 별도 협의 | - | Pro + 전용 대시보드, 슬랙 연동, 맞춤 리포트, 전담 CS |

## 2.7 이메일 발송: 스티비 API

### 선택 근거

| 항목 | 스티비 | AWS SES | SendGrid |
|------|--------|---------|----------|
| 한국어 UI | 네이티브 | 없음 | 있음 |
| 가격 (월 5,000명) | 39,000원 | ~5,000원 | ~15,000원 |
| 뉴스레터 에디터 | 있음 | 없음 | 있음 |
| 구독자 관리 | 있음 | 없음 | 있음 |
| API | 있음 | 있음 | 있음 |
| **추천 용도** | **뉴스레터 + 마케팅** | 트랜잭션 이메일 | 대량 발송 |

### 하이브리드 전략

- **스티비**: 뉴스레터 발송 + 마케팅 이메일 (무료 체험 안내, 전환 캠페인)
- **SMTP (Python smtplib)**: 키워드 알림 실시간 발송 (트랜잭션 이메일)

초기에는 스티비만으로 시작. 일 발송량 1,000건 초과 시 AWS SES 도입.

---

# 3. B2B 영업 실행 플레이북

## 3.1 ICP 기업 리스트 20개사

### A군: 대형 증권사 (자기자본 5조 이상, 준법감시팀 10명+)

| # | 기업명 | 자기자본 | 준법감시팀 규모 | 우선순위 |
|---|--------|---------|---------------|---------|
| 1 | 한국투자증권 | 12.0조 | 15~20명 | A |
| 2 | 미래에셋증권 | 10.3조 | 15~20명 | A |
| 3 | NH투자증권 | 8.4조 | 15~20명 | A |
| 4 | 삼성증권 | 7.4조 | 10~15명 | A |
| 5 | 메리츠증권 | 7.2조 | 10~15명 | A |

### B군: 중형 증권사 + 대형 자산운용사

| # | 기업명 | 유형 | 우선순위 |
|---|--------|------|---------|
| 6 | KB증권 | 증권 | A |
| 7 | 신한투자증권 | 증권 | A |
| 8 | 하나증권 | 증권 | B |
| 9 | 키움증권 | 증권 | B |
| 10 | 대신증권 | 증권 | B |
| 11 | 미래에셋자산운용 | 자산운용 | A |
| 12 | 삼성자산운용 | 자산운용 | A |
| 13 | 한화자산운용 | 자산운용 | B |
| 14 | KB자산운용 | 자산운용 | B |
| 15 | 신한자산운용 | 자산운용 | B |

### C군: 핀테크/보험/기타

| # | 기업명 | 유형 | 우선순위 |
|---|--------|------|---------|
| 16 | 한국투자신탁운용 | 자산운용 | C |
| 17 | 토스증권 | 핀테크 증권 | B |
| 18 | 카카오페이증권 | 핀테크 증권 | C |
| 19 | 삼성생명 | 보험 | C |
| 20 | 한화생명 | 보험 | C |

## 3.2 의사결정자 매핑

### 타겟 직급/부서

| 직급 | 역할 | 접근 전략 |
|------|------|----------|
| **CCO (준법감시인)** | 최종 의사결정자, 예산 승인 | 직접 미팅 요청 (콜드메일 후) |
| **준법감시팀장** | 실무 평가자, 도입 추천 | 무료 체험 제안 + 데모 |
| **준법감시 담당자** | 일상적 사용자, Pain Point 체감 | 뉴스레터 구독 유도 -> 상향 보고 유도 |
| **리스크관리팀** | 인접 부서, 확장 대상 | 금융 규제 리포트 공유 |
| **IT/디지털팀** | 기술 검증, 연동 결정 | API 문서 + 보안 질의 대응 |

### 접근 순서

```
1. 준법감시 담당자 (링크드인/뉴스레터) -> 무료 체험
2. 준법감시팀장 (담당자 추천 or 콜드메일) -> 데모 미팅
3. CCO (팀장 추천) -> 의사결정 미팅
4. IT팀 (CCO 지시) -> 기술 검증
5. 구매/총무팀 -> 계약/결제
```

## 3.3 콜드 이메일 템플릿

### 템플릿 1: 초기 접촉 (금융 규제 모니터링 Pain Point)

```
제목: [한국투자증권] 금융위 보도자료 수동 모니터링, 자동화하실 수 있습니다

안녕하세요, [성함]님.

한국투자증권 준법감시팀에서 금융 규제 모니터링 업무를 담당하고 계신 것으로 알고 있어 연락드립니다.

금융위원회, 금융감독원, 한국은행 등 25개 금융 유관기관의 보도자료를 매일 확인하는 작업, 혹시 수동으로 하고 계신가요?

저희 GovBrief(govbrief.kr)는 정부 51개 부처 보도자료를 매일 자동 크롤링하고 AI로 요약하는 서비스입니다. 특히 금융권 준법감시팀을 위해:

- 금융위/금감원/한은 등 25개 기관 보도자료 실시간 수집
- AI 3줄 요약 + 키워드 자동 추출
- "자본시장법", "과징금", "금소법" 등 키워드 알림 설정
- 매주 금융 규제 동향 분석 리포트 자동 생성

현재 14일 무료 체험을 제공하고 있으며, 별도 설치나 계약 없이 이메일만으로 시작하실 수 있습니다.

혹시 15분 정도 시간을 내어 데모를 보여드려도 될까요?

감사합니다.
[이름]
GovBrief (govbrief.kr)
[이메일] | [전화번호]
```

### 템플릿 2: 팔로업 (3일 후, 미응답 시)

```
제목: Re: [한국투자증권] 금융 규제 모니터링 자동화

안녕하세요, [성함]님.

지난 메일에 이어 한 가지만 더 공유드립니다.

이번 주 금융위원회에서 발표된 [실제 최근 보도자료 제목] 관련,
GovBrief가 자동으로 생성한 요약입니다:

---
[실제 AI 요약 3줄 삽입]
키워드: #자본시장법 #금융소비자보호 #과징금
---

이런 요약이 매일 오전 9시에 이메일로 도착합니다.
첨부한 샘플 주간 리포트도 참고해 주세요.

무료 체험 신청: govbrief.kr/pro

감사합니다.
[이름]
```

### 템플릿 3: 제안서 발송 (관심 표명 후)

```
제목: [한국투자증권] GovBrief Pro 서비스 제안서

안녕하세요, [성함]님.

관심 가져주셔서 감사합니다.
요청하신 GovBrief Pro 서비스 제안서를 첨부합니다.

[첨부: GovBrief_Pro_제안서_한국투자증권.pdf]

핵심 내용 요약:

1. 서비스 범위
   - 금융 유관기관 25개 보도자료 실시간 수집 + AI 요약
   - 맞춤 키워드 알림 (무제한)
   - 주간/월간 금융 규제 동향 분석 리포트
   - API 접근권 (사내 시스템 연동 가능)

2. 가격
   - Pro 플랜: 월 290,000원 (VAT 별도)
   - 연간 계약 시: 월 242,000원 (2개월 무료)
   - 14일 무료 체험 후 결정

3. 도입 절차
   - 무료 체험 -> 키워드 설정 (30분) -> 2주 사용 -> 유료 전환 결정

편하신 시간에 30분 정도 화상 미팅으로 데모를 보여드리면
더 구체적으로 논의할 수 있을 것 같습니다.

이번 주 중 가능하신 시간이 있으실까요?

감사합니다.
[이름]
GovBrief (govbrief.kr)
```

## 3.4 링크드인 아웃리치 스크립트

### 연결 요청 메시지 (300자 이내)

```
안녕하세요, [성함]님. [회사명] 준법감시팀에서 일하고 계신 것으로 알고 연결 요청드립니다.

저는 정부 보도자료 AI 요약 서비스(govbrief.kr)를 운영하고 있는데, 금융 규제 모니터링 자동화에 대해 의견을 나누고 싶습니다.

연결 수락해 주시면 감사하겠습니다.
```

### 연결 수락 후 첫 DM

```
연결 수락 감사합니다, [성함]님!

한 가지 질문 드려도 될까요? 현재 금융위/금감원 보도자료 모니터링을 어떤 방식으로 하고 계신가요?

저희 서비스에서 매일 금융 유관기관 25개 보도자료를 자동 수집하고 AI로 요약해서 이메일로 보내드리는데, 혹시 2주 무료 체험 관심 있으시면 이메일 주소 알려주세요.

govbrief.kr/pro 에서 샘플도 확인하실 수 있습니다.
```

## 3.5 무료 체험 -> 유료 전환 이메일 시퀀스

### Day 1: 환영 이메일

```
제목: GovBrief Pro 무료 체험이 시작되었습니다

[성함]님, 환영합니다!

오늘부터 14일간 GovBrief Pro를 무료로 이용하실 수 있습니다.

시작 가이드:
1. 내일 오전 9시, 첫 금융 규제 브리핑 이메일이 도착합니다
2. govbrief.kr/pro/dashboard 에서 키워드 알림을 설정해 보세요
3. 추천 키워드: 자본시장법, 금소법, 과징금, 인가, 제재

궁금한 점이 있으시면 이 이메일에 바로 답장해 주세요.
```

### Day 3: 가치 확인

```
제목: [성함]님, 3일간 금융 규제 브리핑 받아보셨나요?

지난 3일간 GovBrief가 전달한 금융 보도자료:
- 금융위원회: [X]건
- 금융감독원: [X]건
- 한국은행: [X]건

이 중 키워드 알림으로 매칭된 건: [X]건

혹시 놓친 키워드가 있으시면 추가해 보세요.
govbrief.kr/pro/dashboard -> 알림 설정
```

### Day 7: 중간 점검 + 주간 리포트

```
제목: [성함]님의 첫 주간 금융 규제 리포트

1주차 활용 현황:
- 수신한 브리핑: [X]건
- 키워드 알림: [X]건
- 열람한 보도자료: [X]건

첨부: 이번 주 금융 규제 주간 분석 리포트 (PDF)

무료 체험 남은 기간: 7일
```

### Day 11: 유료 전환 안내

```
제목: 무료 체험 3일 남았습니다 - 구독 안내

[성함]님, 지난 11일간 GovBrief Pro를 통해:
- 총 [X]건의 금융 보도자료 브리핑 수신
- [X]건의 키워드 알림 매칭
- [X]회 대시보드 접속

Pro 구독을 시작하시면:
- 월 290,000원 (VAT 별도)
- 연간 결제 시 월 242,000원 (2개월 무료)
- 세금계산서 자동 발행

구독 시작: govbrief.kr/pro/subscribe
```

### Day 14: 만료 알림

```
제목: 오늘 무료 체험이 종료됩니다

[성함]님, 오늘 GovBrief Pro 무료 체험이 종료됩니다.

구독하지 않으시면 내일부터:
- 매일 금융 규제 브리핑 이메일이 중단됩니다
- 키워드 알림이 비활성화됩니다
- 주간 리포트를 받으실 수 없습니다

지금 구독 시작: govbrief.kr/pro/subscribe

또는, 체험 기간 연장이 필요하시면 이 이메일에 답장해 주세요.
```

## 3.6 가격 협상 대응 가이드

| 고객 반론 | 대응 방법 |
|----------|----------|
| "월 29만원은 비싸다" | "현재 모니터링에 투입되는 인건비를 계산해 보셨나요? 담당자 1명이 하루 1시간 소요 시 월 인건비 약 100만원. GovBrief는 그 1/3 비용으로 더 정확하고 빠릅니다." |
| "무료 사이트로 충분하다" | "govbrief.kr 무료 버전은 일반 요약만 제공합니다. Pro는 키워드 알림, 맞춤 리포트, API 연동이 핵심입니다. 준법감시 업무에서 '놓치지 않는 것'의 가치가 월 29만원보다 큽니다." |
| "사내 결재가 어렵다" | "연간 계약 시 348만원입니다. 교육훈련비나 정보서비스 구독료로 처리 가능합니다. 참고용 품의서 양식을 보내드릴 수 있습니다." |
| "다른 서비스도 검토 중이다" | "어떤 서비스를 검토 중이신가요? (경쟁사 파악) 저희는 정부 보도자료 전문으로, 51개 부처 전수 커버리지와 금융 6개 서브카테고리 분류가 차별점입니다. 2주 무료 체험으로 직접 비교해 보시겠습니까?" |
| "1명만 쓸 건데 팀 라이선스가 필요한가" | "Pro 플랜은 1계정 기준입니다. 팀 전체가 사용하시려면 Enterprise 플랜(별도 협의)을 추천드립니다. 단, 1명이 수신한 브리핑을 사내 공유하시는 건 자유롭습니다." |

---

# 4. 랜딩페이지 & 마케팅

## 4.1 govbrief.kr/pro 랜딩페이지 와이어프레임

### 섹션 1: 히어로

```
[배경: 어두운 네이비 그라데이션]

금융 규제 보도자료,
AI가 매일 읽고 요약합니다.

금융위원회, 금융감독원, 한국은행 등 25개 금융기관
보도자료를 실시간 수집하고 3줄로 요약합니다.
놓치면 안 되는 규제 변화, 이제 자동으로 받으세요.

[CTA 버튼: "14일 무료 체험 시작" -> 이메일 입력 폼]

아래 텍스트: 신용카드 불필요 | 설치 없음 | 30초면 시작
```

### 섹션 2: 문제 제기

```
매일 아침, 이런 일을 하고 계신가요?

[ ] 금융위원회 홈페이지 접속해서 새 보도자료 확인
[ ] 금융감독원 보도자료 페이지 스크롤
[ ] 한국은행 통화정책 발표 확인
[ ] 한국거래소 시장감시 공지 체크
[ ] 공정거래위원회 제재 결정 확인
... x 25개 기관, 매일 반복

준법감시팀 담당자의 하루 1시간이
여기에 소모되고 있습니다.
```

### 섹션 3: 솔루션 소개

```
GovBrief Pro가 대신합니다.

[카드 1] 실시간 수집
51개 부처 + 25개 금융기관 보도자료
매일 자동 크롤링 (일 평균 100건)

[카드 2] AI 3줄 요약
핵심 정책 / 주요 수치 / 영향 대상
전문 분석가 수준의 요약

[카드 3] 키워드 알림
"자본시장법", "과징금", "금소법" 등
내 업무와 관련된 보도자료만 즉시 알림

[카드 4] 주간 리포트
McKinsey 스타일 금융 규제 동향 분석
PDF 다운로드 + 이메일 수신
```

### 섹션 4: 실제 예시

```
오늘의 금융 규제 브리핑 (실시간 데이터)

[실제 금융위원회 최신 보도자료 AI 요약 예시]
[실제 금융감독원 최신 보도자료 AI 요약 예시]
[실제 한국은행 최신 보도자료 AI 요약 예시]

"이런 브리핑이 매일 오전 9시에 이메일로 도착합니다."
```

### 섹션 5: 가격

```
                  Trial          Pro              Enterprise
가격              무료 14일       월 290,000원       별도 협의
                                (연간 시 242,000원)

기관 수            금융 25개       전체 51개+25개      전체
키워드 알림        3개             무제한              무제한
주간 리포트        X               O                  O + 맞춤 리포트
API 접근          X               O                  O
슬랙 연동          X               X                  O
전담 CS           X               이메일              전담 매니저
세금계산서         X               자동 발행           자동 발행

[CTA: "14일 무료 체험 시작"]
```

### 섹션 6: FAQ

```
Q: 무료 체험 후 자동 결제되나요?
A: 아닙니다. 무료 체험 종료 후 직접 구독을 결정하셔야 합니다.
   신용카드 정보를 미리 입력하지 않습니다.

Q: 데이터의 정확도는 어느 정도인가요?
A: 정부 부처 공식 보도자료를 원문 그대로 수집하며, AI 요약의
   정확도는 90% 이상입니다. 원문 링크가 항상 함께 제공됩니다.

Q: 사내 시스템과 연동할 수 있나요?
A: Pro 플랜부터 REST API를 제공합니다. 사내 인트라넷, 슬랙,
   이메일 등 다양한 시스템과 연동 가능합니다.

Q: 공공데이터 활용이 법적으로 문제없나요?
A: 정부 보도자료는 공공누리 제1유형(출처표시)으로 상업적 이용이
   허용됩니다. 공공데이터법 제3조에 근거합니다.

Q: 세금계산서를 발행해 주나요?
A: 매월 자동으로 전자세금계산서를 발행합니다.
```

### 섹션 7: CTA (마무리)

```
지금 시작하세요.

매일 1시간의 규제 모니터링 시간을 절약하세요.
14일 무료 체험, 신용카드 불필요.

[이메일 입력] [무료 체험 시작]
```

## 4.2 링크드인 콘텐츠 캘린더 (12주, 주 2회)

### 콘텐츠 전략
- 화요일: 교육/인사이트 콘텐츠 (금융 규제 트렌드)
- 금요일: 제품/사례 콘텐츠 (GovBrief 활용 사례)

| 주차 | 화요일 주제 | 금요일 주제 |
|------|-----------|-----------|
| W1 | "금융사 준법감시팀이 매일 확인해야 하는 정부 사이트 25개 (리스트)" | "이 25개를 자동으로 확인하는 방법을 만들었습니다 (GovBrief 소개)" |
| W2 | "이번 주 금융위원회 핵심 보도자료 3건 AI 요약" | "준법감시 업무에서 '놓치면 안 되는' 보도자료를 놓치지 않는 법" |
| W3 | "2026년 상반기 금융 규제 변화 총정리 (인포그래픽)" | "GovBrief 무료 체험 시작한 증권사 담당자의 첫 반응" |
| W4 | "금감원 제재 사례 분석: 보도자료를 미리 확인했더라면" | "키워드 알림 기능으로 '자본시장법' 관련 보도자료만 받기" |
| W5 | "RegTech 글로벌 트렌드: 규제 모니터링 자동화가 필수인 이유" | "주간 금융 규제 리포트 샘플 공개 (PDF)" |
| W6 | "금융위원회 vs 금융감독원: 보도자료 패턴 분석" | "데모 영상: GovBrief Pro 대시보드 3분 투어" |
| W7 | "한국은행 금리 결정 전후, 관련 보도자료 AI 분석" | "무료 체험 사용자 피드백: '매일 1시간 절약된다'" |
| W8 | "공정거래위원회 과징금 트렌드 (최근 6개월 데이터)" | "API 연동 가이드: 사내 시스템에 규제 알림 연결하기" |
| W9 | "ESG 관련 금융 규제 동향 2026 하반기 전망" | "Pro 구독 시작 고객 인터뷰 (익명)" |
| W10 | "금소법 시행 이후 금융사 준법감시 업무 변화" | "연간 구독으로 2개월 무료: 지금 전환하면 이득인 이유" |
| W11 | "AI가 요약한 이번 주 금융 보도자료 TOP 5" | "GovBrief를 도입한 팀의 업무 효율 개선 사례" |
| W12 | "2026년 하반기 금융 규제 일정 프리뷰" | "12주 여정 정리: GovBrief가 지금까지 수집한 숫자들" |

### 게시글 형식 가이드
- 첫 2줄에 후크 (관심 끌기)
- 본문 5~7줄 (핵심 인사이트)
- CTA 1줄 (링크 or 질문)
- 해시태그 5개: #금융규제 #준법감시 #RegTech #GovBrief #금융보도자료

## 4.3 금융 규제 뉴스레터 포맷

### 레이아웃

```
============================================================
GovBrief 금융 규제 데일리 브리핑
2026-04-01 (수) | govbrief.kr
============================================================

[오늘의 핵심] (1~2건, 별표)

  ★ 금융위원회 | 자본시장법 시행령 개정안 입법예고
     - 요약: 자본시장법 시행령 개정안이 입법예고되었다. 주요 내용은
       소수주주권 행사 요건 완화와 공매도 규제 강화이다.
       2026년 7월 1일부터 시행 예정이다.
     - 키워드: #자본시장법 #시행령개정 #소수주주권 #공매도
     - 원문: [링크]

------------------------------------------------------------

[금융정책] (3~5건)

  1. 금융위원회 | 보도자료 제목
     요약 3줄 | 키워드 | [원문]

  2. 기획재정부 | 보도자료 제목
     요약 3줄 | 키워드 | [원문]

[감독/규제] (2~3건)

  3. 금융감독원 | 보도자료 제목
     요약 3줄 | 키워드 | [원문]

[시장/통화] (1~2건)

  4. 한국은행 | 보도자료 제목
     요약 3줄 | 키워드 | [원문]

[정책금융] (1~2건)

  5. 한국산업은행 | 보도자료 제목
     요약 3줄 | 키워드 | [원문]

------------------------------------------------------------

[차주 금융 일정] (금요일 발송 시에만 포함)
  - 04/07(월) 금융위원회 정례회의
  - 04/08(화) 한국은행 금통위
  - 04/10(목) 금감원 검사결과 공개

------------------------------------------------------------

이 브리핑은 GovBrief Pro에서 자동 생성되었습니다.
키워드 알림 설정: govbrief.kr/pro/dashboard
구독 관리: govbrief.kr/pro/settings
============================================================
```

## 4.4 SEO 키워드 전략

### 핵심 키워드 (검색량 순)

| 키워드 | 월 검색량 (추정) | 경쟁도 | 콘텐츠 타입 |
|--------|----------------|--------|------------|
| 금융위원회 보도자료 | 2,000+ | 낮음 | 자동 생성 (일별 페이지) |
| 금융감독원 보도자료 | 1,500+ | 낮음 | 자동 생성 (일별 페이지) |
| 한국은행 보도자료 | 1,000+ | 낮음 | 자동 생성 (일별 페이지) |
| 정부 보도자료 | 3,000+ | 중간 | 메인 랜딩페이지 |
| 금융 규제 동향 | 500+ | 중간 | 주간 리포트 페이지 |
| 준법감시 도구 | 200+ | 낮음 | /pro 랜딩페이지 |
| RegTech 한국 | 100+ | 낮음 | 블로그 포스트 |
| 자본시장법 개정 | 500+ | 중간 | 자동 생성 (키워드별) |
| 금소법 | 800+ | 중간 | 자동 생성 (키워드별) |

### SEO 실행 전략

1. **자동 생성 SEO 페이지**: 매일 크롤링한 보도자료를 기관별/키워드별 정적 HTML로 생성 (기존 static_gen.py 확장)
2. **URL 구조**: `govbrief.kr/articles/2026-04-01/금융위원회` (날짜+기관별)
3. **메타 태그**: 보도자료 제목 + AI 요약을 description에 자동 삽입
4. **구조화 데이터**: Article schema.org 마크업 적용
5. **내부 링크**: 키워드 기반 관련 보도자료 자동 연결

---

# 5. 법적/사업자 준비 체크리스트

## 5.1 사업자 등록

### 개인사업자 vs 법인

| 항목 | 개인사업자 | 법인 (주식회사) |
|------|----------|---------------|
| 설립 비용 | 0원 | 50~100만원 (등록면허세+법무사) |
| 소요 기간 | 3~5일 | 1~2주 |
| 세율 | 종합소득세 6~45% | 법인세 9~24% |
| 대외 신뢰도 | 보통 | 높음 |
| 투자 유치 | 어려움 | 가능 |
| **추천 시점** | **Year 1 (즉시)** | Year 2 (ARR 1억+ 시) |

### 개인사업자 등록 절차 (즉시 실행)

```
1. 홈택스 접속 (hometax.go.kr)
2. [신청/제출] -> [사업자등록 신청]
3. 입력 정보:
   - 상호: 거브브리프 (또는 GovBrief)
   - 업태: 정보통신업
   - 종목: 소프트웨어 개발 및 공급업 (업종코드: 620202)
         + 데이터베이스 및 온라인정보 제공업 (업종코드: 631209)
   - 사업장 소재지: 자택 (재택 가능)
   - 개업일: 신청일
4. 제출 -> 3~5 영업일 후 사업자등록증 발급
```

## 5.2 통신판매업 신고

### 절차

```
1. 사업자등록증 발급 완료 (선행 조건)
2. Toss Payments 가입 -> "구매안전서비스 이용확인증" 발급
3. 정부24 (gov.kr) 접속
4. [통신판매업 신고] 검색
5. 신고서 작성:
   - 호스트서버 소재지: GitHub Pages (미국) 또는 서버 소재지
   - 통신판매 유형: 전자상거래 (인터넷)
   - 취급 상품: 소프트웨어 서비스 (SaaS)
6. 필요 서류: 사업자등록증, 구매안전서비스 이용확인증
7. 등록면허세 납부: 12,000~40,500원 (지역별 상이)
8. 처리 기간: 3~5 영업일
```

## 5.3 개인정보처리방침 필수 항목

```
1. 개인정보의 처리 목적
   - 회원 관리 (가입, 인증, 서비스 제공)
   - 서비스 제공 (보도자료 요약, 키워드 알림, 리포트)
   - 결제 처리 (구독 관리, 세금계산서 발행)

2. 수집하는 개인정보 항목
   - 필수: 이메일, 비밀번호, 회사명
   - 선택: 이름, 전화번호, 부서명
   - 자동 수집: IP 주소, 접속 로그, 쿠키

3. 개인정보의 보유 및 이용 기간
   - 회원 탈퇴 시까지 (탈퇴 후 30일 이내 파기)
   - 결제 기록: 5년 (전자상거래법)

4. 개인정보의 제3자 제공
   - Toss Payments (결제 처리): 결제 정보
   - 스티비 (이메일 발송): 이메일 주소
   - 제공 동의 별도 수집

5. 개인정보 처리 위탁
   - 위탁업체 및 위탁 업무 목록 공개

6. 정보주체의 권리/의무
   - 열람, 정정, 삭제, 처리정지 요구권

7. 개인정보의 파기 절차 및 방법
   - 전자 파일: 복구 불가능한 방법으로 삭제
   - 종이 문서: 파쇄

8. 개인정보 보호책임자
   - 이름, 직위, 연락처

9. 개인정보 자동 수집 장치의 설치/운영/거부
   - 쿠키 사용 목적, 거부 방법

10. 시행일
```

## 5.4 이용약관 핵심 조항

```
1. 목적
   - 서비스 이용 조건 및 권리/의무 규정

2. 서비스 내용
   - 정부 보도자료 수집, AI 요약, 키워드 알림, 리포트 제공
   - 서비스 수준 (SLA): 가용성 99% (월간 기준)

3. 이용 요금 및 결제
   - 플랜별 가격, 결제 주기, 환불 정책
   - 환불: 결제일로부터 7일 이내 전액 환불
   - 세금계산서 발행 기준

4. 면책 사항
   - AI 요약의 정확성에 대한 면책 (투자/법률 자문 목적 불가)
   - 정부 부처 웹사이트 장애로 인한 수집 불가 시 면책
   - 원문 보도자료 내용에 대한 책임은 해당 부처에 있음

5. 저작권 및 지적재산권
   - 원문 보도자료: 공공누리 라이선스 적용
   - AI 요약 및 분석: GovBrief 저작권
   - 사용자 재배포 금지 (사내 공유는 허용)

6. 계약 해지
   - 사용자: 언제든 해지 가능 (잔여 기간 일할 환불)
   - 서비스 제공자: 이용약관 위반 시 해지 가능

7. 분쟁 해결
   - 관할 법원: 서울중앙지방법원
```

## 5.5 공공데이터 상업적 활용 법적 근거

### 적용 법률

1. **공공데이터의 제공 및 이용 활성화에 관한 법률 (공공데이터법)**
   - 제1조 (목적): 공공데이터의 이용활성화를 통해 국민 편의 증진 및 국가 경쟁력 강화
   - 제3조 (공공데이터 제공 원칙): 공공기관은 보유한 공공데이터를 적극 제공하여야 한다
   - 제17조 (이용자의 권리): 누구든지 공공데이터를 이용할 수 있다

2. **저작권법 제24조의2 (공공저작물의 자유이용)**
   - 국가 또는 지방자치단체가 업무상 작성한 저작물은 자유이용 가능
   - 단, 공공누리 유형에 따라 조건 상이

3. **공공누리 유형별 적용**
   - 제1유형 (출처표시): 상업적 이용 가능, 변경 가능 -> 대부분의 보도자료 해당
   - 제2유형 (출처표시+상업적 이용금지): 해당 콘텐츠 제외 필요
   - 제3유형 (출처표시+변경금지): 원문 변경 불가 (AI 요약은 "별도 저작물"로 해석 가능)
   - 제4유형 (출처표시+상업적이용금지+변경금지): 해당 콘텐츠 제외 필요

### 실행 체크리스트

```
[O] 각 보도자료 원문 출처 명시 (부처명 + 원문 링크)
[O] AI 요약은 원문의 "변환"이 아닌 "별도 창작물"로 분류
[O] 공공누리 제2유형/제4유형 콘텐츠는 유료 서비스에서 제외
[O] 법률 자문 1회 진행 (비용: 30~50만원)
    - 추천: 정보통신/데이터 전문 변호사
    - 확인 사항: 크롤링 합법성, AI 요약 저작권, 상업적 이용 범위
```

---

# 6. 수익 시뮬레이션

## 6.1 비용 구조

### 고정비 (월간)

| 항목 | 현재 | MVP 후 | 비고 |
|------|------|--------|------|
| 서버/호스팅 | 0원 (GitHub Pages) | 50,000원 (VPS) | FastAPI 서버용 |
| 도메인 | 포함 | 포함 | govbrief.kr |
| LLM API | ~100,000원 | ~150,000원 | qwen3.5:35b 자체 호스팅 or API |
| 스티비 | 0원 | 39,000원 | 스탠다드 (5,000명) |
| Toss Payments | 0원 | 0원 (거래 수수료만) | |
| **소계** | **~100,000원** | **~239,000원** | |

### 변동비 (건당)

| 항목 | 단가 |
|------|------|
| Toss Payments 수수료 | 결제액의 3.3~4.3% |
| 이메일 발송 (초과분) | 건당 ~5원 |
| LLM 추가 사용 | 건당 ~10원 |

### 손익분기점

```
월 고정비: 239,000원
Pro 구독 1개사 수익: 290,000원 - 결제수수료 ~12,000원 = 278,000원

손익분기점 = 1개사 (유료 고객 1개사면 즉시 흑자)
```

## 6.2 12개월 MRR 프로젝션

### Base 시나리오 (현실적)

| 월 | 무료체험 누적 | 신규 유료 | 유료 누적 | MRR | 비용 | 순이익 |
|----|-------------|----------|----------|------|------|--------|
| M1 | 10 | 0 | 0 | 0 | 239,000 | -239,000 |
| M2 | 25 | 0 | 0 | 0 | 239,000 | -239,000 |
| M3 | 40 | 2 | 2 | 580,000 | 263,000 | 317,000 |
| M4 | 55 | 1 | 3 | 870,000 | 275,000 | 595,000 |
| M5 | 70 | 2 | 5 | 1,450,000 | 299,000 | 1,151,000 |
| M6 | 90 | 1 | 6 | 1,740,000 | 311,000 | 1,429,000 |
| M7 | 110 | 2 | 8 | 2,320,000 | 335,000 | 1,985,000 |
| M8 | 130 | 2 | 10 | 2,900,000 | 359,000 | 2,541,000 |
| M9 | 150 | 1 | 11 | 3,190,000 | 371,000 | 2,819,000 |
| M10 | 170 | 2 | 13 | 3,770,000 | 395,000 | 3,375,000 |
| M11 | 190 | 2 | 15 | 4,350,000 | 419,000 | 3,931,000 |
| M12 | 210 | 3 | 18 | 5,220,000 | 455,000 | 4,765,000 |

**Year 1 Base 요약**:
- 연말 MRR: 5,220,000원
- ARR 환산: 62,640,000원
- 연간 총 매출: 26,390,000원
- 연간 총 비용: 3,960,000원
- 연간 순이익: 22,430,000원
- 유료 고객: 18개사
- 해지율 가정: 0% (초기 소수 고객, 높은 밀착 관리)

### Best 시나리오 (낙관적)

| 월 | 유료 누적 | MRR | 순이익 |
|----|----------|------|--------|
| M3 | 3 | 870,000 | 607,000 |
| M6 | 10 | 2,900,000 | 2,529,000 |
| M9 | 18 | 5,220,000 | 4,719,000 |
| M12 | 25 | 7,250,000 | 6,675,000 |

**Year 1 Best 요약**:
- 연말 MRR: 7,250,000원
- ARR 환산: 87,000,000원
- 유료 고객: 25개사

### Worst 시나리오 (비관적)

| 월 | 유료 누적 | MRR | 순이익 |
|----|----------|------|--------|
| M3 | 0 | 0 | -263,000 |
| M6 | 2 | 580,000 | 269,000 |
| M9 | 5 | 1,450,000 | 1,079,000 |
| M12 | 8 | 2,320,000 | 1,865,000 |

**Year 1 Worst 요약**:
- 연말 MRR: 2,320,000원
- ARR 환산: 27,840,000원
- 유료 고객: 8개사
- 여전히 흑자 (M6부터)

## 6.3 핵심 지표 계산

### CAC (고객 획득 비용)

```
마케팅 비용 (Year 1):
  - 스티비 구독: 39,000원 x 12 = 468,000원
  - 링크드인 프리미엄 (선택): 60,000원 x 6 = 360,000원
  - 법률 자문: 500,000원 (1회)
  - 기타 (디자인, 도구): 300,000원
  총 마케팅 비용: 1,628,000원

  인건비 (영업 시간): 본인 시간이므로 별도 산정하지 않음

Base 시나리오 CAC = 1,628,000 / 18개사 = 90,444원/사
```

### LTV (고객 생애 가치)

```
월 ARPU: 290,000원
월 해지율: 3% (B2B 평균)
평균 고객 수명: 1 / 0.03 = 33개월

Gross Margin: 약 85% (비용 대부분 고정비)

LTV = 290,000 x 33 x 0.85 = 8,131,500원
```

### LTV:CAC 비율

```
LTV / CAC = 8,131,500 / 90,444 = 89.9x

(B2B SaaS 건전 기준: 3x 이상 -> 매우 건전)
```

### Payback Period

```
CAC / 월 ARPU = 90,444 / 290,000 = 0.31개월

-> 첫 달 결제로 CAC 즉시 회수
```

## 6.4 시나리오별 주요 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| AI 요약 품질 불만족 | 해지율 상승 | 금융 도메인 특화 프롬프트 + 사람 검증 파일럿 |
| 영업 실패 (무료체험 전환율 0%) | 매출 0 | 가격 인하 (월 19만원), 개인 구독 플랜 추가 |
| 정부 웹사이트 구조 변경 | 크롤링 중단 | 크롤러 모듈화 (이미 34개 독립 크롤러), 빠른 수정 |
| 경쟁사 진입 | 가격 경쟁 | 금융 특화 + 51개 부처 커버리지 차별화 |
| 법적 이슈 (크롤링 금지) | 서비스 중단 | 공공데이터 포털 API 대체, 법률 자문 선제 확보 |
| 1인 번아웃 | 서비스 품질 저하 | 자동화 극대화, M6부터 파트타임 CS 채용 고려 |

---

# 부록 A: 기술 의존성 추가 목록

```
# requirements.txt 추가 항목
fastapi>=0.115.0
uvicorn>=0.34.0
python-jose[cryptography]>=3.3.0   # JWT
passlib[bcrypt]>=1.7.4             # 비밀번호 해싱
python-multipart>=0.0.17            # 폼 데이터
httpx>=0.28.0                       # 비동기 HTTP (Toss API)
pydantic[email]>=2.12.0             # 이메일 검증
apscheduler>=3.11.0                 # 정기결제 스케줄러
```

# 부록 B: 배포 인프라

### 현재 (무료)
- GitHub Pages: 정적 사이트 (govbrief.kr)
- GitHub Actions: 크롤링 자동화 (일 2회)

### MVP 후 (월 5만원)
- VPS (Vultr/DigitalOcean Seoul): FastAPI + SQLite
  - 2 vCPU, 4GB RAM, 80GB SSD = 월 ~$24
- GitHub Pages: 정적 사이트 유지
- GitHub Actions: 크롤링 + 알림 엔진 트리거

### 배포 구조

```
[GitHub Actions] --cron 매일 7:30, 12:30-->
    |
    +-- 크롤링 + LLM 요약 + DB 저장
    +-- POST /api/v1/internal/trigger-alerts (VPS)
    +-- 정적 사이트 생성 -> GitHub Pages

[VPS (Seoul)]
    |
    +-- FastAPI 서버 (uvicorn, 포트 8000)
    +-- SQLite DB (briefingroom.db)
    +-- Nginx 리버스 프록시 (HTTPS)
    +-- Let's Encrypt SSL 인증서
    |
    +-- api.govbrief.kr -> FastAPI
    +-- govbrief.kr/pro -> 정적 HTML (GitHub Pages)
```

---

# 부록 C: Week 1 Day 1 즉시 실행 체크리스트

```
오늘 할 일 (4시간):

[  ] 1. 홈택스 사업자등록 신청 (30분)
       - 업태: 정보통신업
       - 종목: 소프트웨어 개발 및 공급업 (620202)

[  ] 2. govbrief.kr/pro 폴더 생성 + index.html 작성 시작 (2시간)
       - 히어로 섹션 + CTA (이메일 수집 폼)
       - 핵심: "14일 무료 체험 시작" 버튼

[  ] 3. 스티비 계정 생성 + 주소록 설정 (30분)
       - "금융 규제 데일리 브리핑" 주소록 생성
       - "무료체험" 태그 설정

[  ] 4. 금융 카테고리 데일리 브리핑 이메일 템플릿 제작 (1시간)
       - 기존 static_gen.py 출력물에서 금융 카테고리만 추출
       - 스티비 이메일 템플릿에 맞게 포맷

내일 할 일:
[  ] 5. 랜딩페이지 완성 + 배포
[  ] 6. 링크드인 프로필 업데이트
[  ] 7. ICP 기업 20개 담당자 LinkedIn 탐색 시작
```

---

*이 문서는 GovBrief(govbrief.kr) 상업화를 위한 실행 플레이북입니다.*
*코드베이스 분석, 시장 조사, 법적 검토를 기반으로 2026-03-29에 작성되었습니다.*
