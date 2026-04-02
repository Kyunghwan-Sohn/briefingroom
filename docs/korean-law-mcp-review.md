# korean-law-mcp 활용 검토 보고서

> 검토일: 2026-03-31
> 대상: https://github.com/chrisryugj/korean-law-mcp
> 목적: govbrief.kr 서비스에 korean-law-mcp 64개 도구 활용 가능성 분석

---

## 1. korean-law-mcp 제공 도구 전체 목록 (64개)

korean-law-mcp는 한국 법제처(law.go.kr) Open API를 MCP(Model Context Protocol) 서버로 래핑한 오픈소스 프로젝트이다. 법제처가 제공하는 거의 모든 API 엔드포인트를 MCP 도구로 노출한다.

### 1-1. 법령 검색 (Law Search) - 8개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `search_law` | 법령 키워드 검색 | `query`, `display`, `page` |
| `search_law_by_name` | 법령명 정확 검색 | `lawName` |
| `search_law_by_mst` | 법령일련번호로 검색 | `MST` |
| `search_law_by_law_id` | 법령ID로 검색 | `lawId` |
| `search_law_list` | 법령 목록 검색 (필터링) | `target`, `query`, `lawType`, `organ` |
| `search_law_by_date` | 시행일자 기준 검색 | `startDate`, `endDate` |
| `search_law_history` | 법령 연혁 검색 | `lawName`, `MST` |
| `search_law_amendment` | 법령 개정 이력 | `MST` |

### 1-2. 법령 본문 조회 (Law Content) - 10개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `get_law_full_text` | 법령 전문 조회 | `MST` |
| `get_law_article` | 특정 조문 조회 | `MST`, `articleNo` |
| `get_law_articles_range` | 조문 범위 조회 | `MST`, `fromArticle`, `toArticle` |
| `get_law_chapter` | 장/편 단위 조회 | `MST`, `chapter` |
| `get_law_addendum` | 부칙 조회 | `MST` |
| `get_law_table` | 별표/서식 조회 | `MST`, `tableNo` |
| `get_law_attached_file` | 첨부파일 조회 | `MST`, `fileNo` |
| `get_law_enacted_text` | 제정 당시 본문 | `MST` |
| `get_law_previous_text` | 구법 본문 조회 | `MST`, `revisionDate` |
| `get_law_comparison` | 신구 조문 대조표 | `MST` |

### 1-3. 판례 검색/조회 (Precedent) - 8개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `search_precedent` | 판례 키워드 검색 | `query`, `display`, `page` |
| `search_precedent_by_case_no` | 사건번호로 검색 | `caseNo` |
| `get_precedent_detail` | 판례 상세 조회 | `precedentId` |
| `get_precedent_full_text` | 판례 전문 | `precedentId` |
| `search_precedent_by_law` | 특정 법령 관련 판례 | `lawName`, `articleNo` |
| `search_precedent_by_court` | 법원별 판례 검색 | `courtName`, `query` |
| `search_precedent_by_date` | 선고일 기준 검색 | `startDate`, `endDate` |
| `get_precedent_summary` | 판례 요지 | `precedentId` |

### 1-4. 해석례 (Interpretation) - 6개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `search_interpretation` | 해석례 검색 | `query`, `display` |
| `get_interpretation_detail` | 해석례 상세 | `interpretationId` |
| `search_interpretation_by_law` | 법령별 해석례 | `lawName` |
| `search_interpretation_by_organ` | 기관별 해석례 | `organ` |
| `search_interpretation_by_date` | 일자별 해석례 | `startDate`, `endDate` |
| `get_interpretation_full_text` | 해석례 전문 | `interpretationId` |

### 1-5. 행정규칙 (Administrative Rules) - 6개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `search_admin_rule` | 행정규칙 검색 | `query`, `display` |
| `get_admin_rule_detail` | 행정규칙 상세 | `adminRuleId` |
| `get_admin_rule_full_text` | 행정규칙 전문 | `adminRuleId` |
| `search_admin_rule_by_organ` | 소관기관별 검색 | `organ` |
| `search_admin_rule_by_type` | 유형별 검색 | `ruleType` |
| `search_admin_rule_by_date` | 일자별 검색 | `startDate`, `endDate` |

### 1-6. 자치법규 (Local Ordinance) - 6개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `search_local_law` | 자치법규 검색 | `query`, `display` |
| `get_local_law_detail` | 자치법규 상세 | `localLawId` |
| `get_local_law_full_text` | 자치법규 전문 | `localLawId` |
| `search_local_law_by_region` | 지역별 검색 | `region` |
| `search_local_law_by_type` | 유형별 검색 | `lawType` |
| `search_local_law_by_date` | 일자별 검색 | `startDate`, `endDate` |

### 1-7. 헌재결정례 (Constitutional Court) - 6개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `search_constitutional` | 헌재결정례 검색 | `query`, `display` |
| `get_constitutional_detail` | 헌재결정례 상세 | `constitutionalId` |
| `get_constitutional_full_text` | 헌재결정례 전문 | `constitutionalId` |
| `search_constitutional_by_case_no` | 사건번호 검색 | `caseNo` |
| `search_constitutional_by_type` | 결정유형별 검색 | `decisionType` |
| `search_constitutional_by_date` | 일자별 검색 | `startDate`, `endDate` |

### 1-8. 입법예고 (Legislative Notice) - 6개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `search_legislative_notice` | 입법예고 검색 | `query`, `display` |
| `get_legislative_notice_detail` | 입법예고 상세 | `noticeId` |
| `search_legislative_notice_by_organ` | 소관부처별 검색 | `organ` |
| `search_legislative_notice_by_status` | 진행상태별 검색 | `status` |
| `search_legislative_notice_by_date` | 기간별 검색 | `startDate`, `endDate` |
| `get_legislative_notice_draft` | 입법예고 법률안 원문 | `noticeId` |

### 1-9. 조약 (Treaty) - 4개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `search_treaty` | 조약 검색 | `query`, `display` |
| `get_treaty_detail` | 조약 상세 | `treatyId` |
| `get_treaty_full_text` | 조약 전문 | `treatyId` |
| `search_treaty_by_country` | 국가별 조약 | `country` |

### 1-10. 유틸리티 (Utility) - 4개 도구

| 도구명 | 설명 | 주요 파라미터 |
|--------|------|---------------|
| `get_law_type_list` | 법령 구분 목록 | 없음 |
| `get_organ_list` | 소관부처 목록 | 없음 |
| `get_court_list` | 법원 목록 | 없음 |
| `get_region_list` | 지역(자치단체) 목록 | 없음 |

---

## 2. 우리가 직접 구현한 것 vs MCP로 대체/보강 가능한 것

### 2-1. 현재 law.py 구현 현황

| 기능 | 구현 방식 | 한계 |
|------|-----------|------|
| `search_law()` | 법제처 lawSearch.do API 직접 호출 | 법령 검색만 가능, 판례/해석례 미지원 |
| `get_article_text()` | lawService.do API로 조문 조회 | 단일 조문만, 범위 조회 불가 |
| `extract_law_names()` | 정규식 기반 법령명 추출 | 오탐/미탐 존재 |
| `process_laws_for_items()` | 보도자료-법령 연동 | 최대 3개 법령, 50회 API 제한 |
| SQLite 캐시 | law_cache.db, 30일 TTL | 법령 기본정보만 캐시, 조문은 미캐시 |

### 2-2. 대체 가능성 분석

| 우리 기능 | MCP 대응 도구 | 대체 권장? |
|-----------|---------------|-----------|
| `search_law()` | `search_law`, `search_law_by_name` | 대체 불필요 - 이미 충분 |
| `get_article_text()` | `get_law_article`, `get_law_articles_range` | 보강 가능 - 범위 조회 추가 |
| `extract_law_names()` | 해당 없음 (MCP에 없는 기능) | 유지 - 자체 NLP 기능 |
| SQLite 캐시 | 해당 없음 | 유지 - MCP에는 캐시 없음 |

### 2-3. MCP가 추가로 제공하는 기능 (우리에게 없는 것)

| 카테고리 | 도구 수 | 활용 가치 (govbrief.kr) |
|----------|---------|------------------------|
| 판례 검색/조회 | 8개 | **높음** - 보도자료 관련 판례 자동 연결 |
| 해석례 | 6개 | **높음** - 법령 해석 근거 제공 |
| 입법예고 | 6개 | **매우 높음** - 예정 법령 변경사항 선제 브리핑 |
| 행정규칙 | 6개 | 중간 - 하위법령 추적 |
| 자치법규 | 6개 | 낮음 - 현재 중앙부처 중심 서비스 |
| 헌재결정례 | 6개 | 중간 - 위헌 결정 관련 브리핑 |
| 조약 | 4개 | 낮음 - 외교부 보도자료 한정 |
| 법령 연혁/비교 | 3개 | **높음** - 개정 전후 비교 브리핑 |
| 입법예고 원문 | 1개 | **높음** - 법률안 분석 자동화 |

---

## 3. 활용 시나리오 분석

### 시나리오 A: Claude Code에서 MCP 서버로 연결하여 개발 시 활용

```
적용 난이도: 낮음
가치: 중간
```

- Claude Code의 MCP 설정(`~/.claude/settings.json`)에 korean-law-mcp 추가
- 개발 중 법령 조회, 판례 검색 등을 Claude에게 요청 가능
- 코드 작성 시 법령 조문 참조가 필요할 때 유용
- **한계**: 개발자 도구일 뿐, 프로덕션 서비스에는 직접 영향 없음

```json
{
  "mcpServers": {
    "korean-law": {
      "command": "npx",
      "args": ["-y", "korean-law-mcp"]
    }
  }
}
```

### 시나리오 B: govbrief.kr 백엔드에서 MCP 도구를 직접 호출

```
적용 난이도: 중간~높음
가치: 높음
```

- Python에서 MCP 클라이언트로 korean-law-mcp 서버에 연결
- `mcp` Python SDK (`pip install mcp`) 사용
- subprocess로 Node.js MCP 서버를 stdio로 실행하고 JSON-RPC 통신

```python
# 개념적 구현
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="npx",
    args=["-y", "korean-law-mcp"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("search_precedent", {
            "query": "개인정보보호법 위반"
        })
```

- **장점**: 64개 도구를 모두 활용 가능, 자체 구현 불필요
- **단점**: Node.js 런타임 의존, subprocess 오버헤드, 에러 핸들링 복잡

### 시나리오 C: 사용자에게 MCP 기반 챗봇 제공

```
적용 난이도: 높음
가치: 매우 높음
```

- govbrief.kr에 "법령 AI 어시스턴트" 챗봇 추가
- 사용자 질문 -> Claude API + MCP 도구 -> 법령/판례/해석례 종합 답변
- 예: "개인정보보호법 제15조 관련 최근 판례 알려줘"

- **장점**: 차별화된 서비스, 높은 사용자 가치
- **단점**: Claude API 비용, 응답 지연, MCP 서버 안정성

### 시나리오 D: MCP 도구를 래핑하여 자체 API로 제공

```
적용 난이도: 중간
가치: 중간
```

- MCP 도구 중 필요한 것만 선별하여 REST API로 래핑
- FastAPI 엔드포인트로 노출, 프론트엔드에서 직접 호출
- **더 나은 대안**: 법제처 API를 직접 호출하는 것이 더 단순함 (MCP 래핑은 불필요한 중간 레이어)

### 권장 조합

**1순위: 시나리오 A (즉시 적용)** + **시나리오 B의 선별 적용**

- Claude Code MCP로 개발 생산성 향상 (즉시)
- 판례/해석례/입법예고 3개 카테고리만 Python으로 직접 구현 (MCP 참고)
- law.py에 `search_precedent()`, `search_interpretation()`, `search_legislative_notice()` 추가
- MCP를 참고 구현(reference implementation)으로 활용하되, 프로덕션은 직접 API 호출

---

## 4. 기술적 검토

### 4-1. Node.js 의존성

| 항목 | 상세 |
|------|------|
| 런타임 | Node.js 18+ 필요 |
| 패키지 매니저 | npm/npx |
| 주요 의존성 | `@modelcontextprotocol/sdk`, `node-fetch`, `fast-xml-parser` |
| 설치 방식 | `npx -y korean-law-mcp` (자동 다운로드) |
| 현재 프로젝트 | Python 3.11+, Node.js 미사용 |

**영향**: GitHub Actions에 Node.js 설치 필요. 로컬 개발에서는 npx로 즉시 사용 가능.

### 4-2. Python에서 MCP 호출 가능 여부

**가능하다.** 두 가지 방법:

1. **mcp Python SDK** (공식)
   - `pip install mcp`
   - stdio transport로 Node.js MCP 서버와 통신
   - async/await 필수 (asyncio 기반)
   - 현재 law.py는 동기(requests) 기반 -> 리팩터링 필요

2. **subprocess + JSON-RPC 직접 통신**
   - Node.js 프로세스를 subprocess로 실행
   - stdin/stdout으로 JSON-RPC 2.0 메시지 교환
   - 더 낮은 수준의 제어, 더 복잡한 구현

### 4-3. 원격 서버(fly.dev 등) 활용 시 장단점

korean-law-mcp가 SSE(Server-Sent Events) transport를 지원하는 경우:

| 장점 | 단점 |
|------|------|
| Node.js 로컬 설치 불필요 | 네트워크 지연 추가 (30~100ms) |
| 서버 관리 분리 | 외부 서비스 의존성 증가 |
| 수평 확장 가능 | fly.dev 비용 발생 |
| Python 앱과 독립 배포 | 법제처 API 키 노출 위험 |

### 4-4. 자체 호스팅 시 필요 인프라

| 구성요소 | 상세 |
|----------|------|
| 서버 | Node.js 18+ 실행 가능한 VM/컨테이너 |
| 메모리 | 256MB 이상 (경량 서버) |
| Docker | `FROM node:18-alpine` 기반 이미지 |
| 네트워크 | 법제처 API 접근 가능 (한국 IP 권장) |
| 모니터링 | health check, 로그 수집 |

### 4-5. 최종 기술 판단

> **MCP를 프로덕션에 직접 사용하는 것보다, 법제처 API를 Python에서 직접 호출하는 현재 방식이 더 적합하다.**

이유:
- 불필요한 Node.js 의존성 추가 회피
- subprocess 통신 오버헤드 없음
- 동기 코드(requests) 유지, asyncio 전환 불필요
- 캐시(SQLite) 직접 제어 가능
- korean-law-mcp 소스코드를 참고하여 필요한 API 엔드포인트만 law.py에 추가

---

## 5. finance_law.db와의 시너지

### 5-1. 현재 DB 현황

| 데이터 유형 | 건수 | 출처 |
|-------------|------|------|
| 법령 | 139건 | 금융 관련 법령 선별 수집 |
| 조문 | 3,893건 | 법령별 전체 조문 |
| 판례 | 526건 | 금융 관련 판례 |
| 해석례 | 193건 | 금융 관련 해석례 |
| 행정규칙 | 323건 | 금융위/금감원 규칙 |
| 자치법규 | 309건 | 금융 관련 자치법규 |
| 헌재결정례 | 230건 | 금융 관련 헌재 결정 |
| **합계** | **5,613건** | |

### 5-2. 결합 활용 시나리오

#### A. 보도자료-판례 자동 연결 (가장 즉각적 가치)

```
현재: 보도자료 -> 법령명 추출 -> 법령 검색 -> 기본정보 표시
확장: 보도자료 -> 법령명 추출 -> 법령 검색 + 판례 검색 -> 관련 판례까지 표시
```

- finance_law.db의 526건 판례를 기초 데이터로 활용
- 신규 판례는 법제처 API(MCP 참고)로 실시간 보강
- 브리핑에 "관련 판례 N건" 표시 -> 클릭 시 판례 요지 제공

#### B. 입법예고 모니터링 자동화 (높은 서비스 가치)

```
매일 자동 수집: 입법예고 API -> 금융 관련 필터링 -> 브리핑 생성
```

- 현재 보도자료 중심 서비스에 "예정 법령 변경" 섹션 추가
- "이 법령은 OO 개정이 예고되어 있습니다" 알림
- 텔레그램/인스타그램 채널에 입법예고 속보 발송

#### C. 법령 개정 전후 비교 브리핑

```
법령 개정 보도자료 발생 시:
1. 현행 조문 (finance_law.db)
2. 개정 조문 (법제처 API 실시간 조회)
3. 변경사항 diff 생성
4. 영향 분석 브리핑 자동 생성
```

#### D. 법령-해석례 크로스레퍼런스

```
사용자가 특정 법령 조문 열람 시:
- finance_law.db에서 해당 조문의 해석례 193건 중 관련 건 표시
- 법제처 API로 최신 해석례 추가 조회
- "이 조문에 대한 유권해석 N건" 제공
```

#### E. 종합 법령 브리핑 서비스

```
특정 법령(예: 자본시장법) 대시보드:
- 현행 조문 (finance_law.db: 3,893건)
- 관련 판례 (finance_law.db: 526건 + 실시간 API)
- 관련 해석례 (finance_law.db: 193건 + 실시간 API)
- 관련 행정규칙 (finance_law.db: 323건)
- 관련 보도자료 (law_cache.db article_law 테이블)
- 입법예고 현황 (실시간 API)
```

### 5-3. 구현 우선순위

| 순위 | 기능 | 난이도 | 가치 | 필요 작업 |
|------|------|--------|------|-----------|
| 1 | 입법예고 모니터링 | 낮음 | 매우 높음 | law.py에 `search_legislative_notice()` 추가 |
| 2 | 판례 연결 | 낮음 | 높음 | law.py에 `search_precedent_by_law()` 추가 |
| 3 | 법령 개정 비교 | 중간 | 높음 | law.py에 `get_law_comparison()` 추가 |
| 4 | 해석례 연결 | 낮음 | 중간 | law.py에 `search_interpretation_by_law()` 추가 |
| 5 | 종합 법령 대시보드 | 높음 | 매우 높음 | 프론트엔드 + API 전면 확장 |

---

## 6. 결론 및 권장사항

### 즉시 실행 (이번 주)

1. **Claude Code MCP 설정에 korean-law-mcp 추가** - 개발 시 법령 조회 편의성 확보
2. **korean-law-mcp 소스코드를 참고하여** 법제처 API 엔드포인트 목록 정리

### 단기 (1-2주)

3. **law.py에 3개 함수 추가** (법제처 API 직접 호출, MCP 미사용):
   - `search_legislative_notice()` - 입법예고 검색
   - `search_precedent_by_law()` - 법령별 판례 검색
   - `get_law_comparison()` - 신구 조문 대조

4. **finance_law.db 연동**: 보도자료 브리핑에 관련 판례/해석례 건수 표시

### 중기 (1개월)

5. **입법예고 모니터링 파이프라인**: 매일 자동 수집 -> 금융 관련 필터링 -> 텔레그램 발송
6. **법령 개정 브리핑 자동화**: 개정 보도자료 감지 시 신구대조표 자동 생성

### 핵심 판단

> korean-law-mcp는 **법제처 API의 우수한 참고 구현(reference implementation)**으로 활용한다.
> 프로덕션에서는 **Python으로 직접 API 호출**하는 현재 아키텍처를 유지한다.
> MCP 프로토콜 자체는 Claude Code 개발 도구로만 활용한다.
> 가장 큰 가치는 **우리가 아직 활용하지 않는 API 엔드포인트의 발견** (입법예고, 판례, 해석례, 신구대조)에 있다.
