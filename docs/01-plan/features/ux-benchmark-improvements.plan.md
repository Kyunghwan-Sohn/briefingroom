# Plan: UX 벤치마크 기반 개선사항 — govbrief.kr
**작성일:** 2026-03-28
**작성자:** PM Agent
**상태:** Draft (CTO 검토 대기)
**버전:** v1.0

---

## 1. Overview

해외 유사 서비스 8종을 벤치마크하여 govbrief.kr의 UI/UX 개선점을 발굴하고 우선순위화한다. 분석 대상: GovTrack.us, TheyWorkForYou.com, Politico.eu, Gov.uk, Axios.com, The Skimm/Morning Brew, Feedly/Inoreader, Naver/Daum News.

**현재 스택 제약:** GitHub Pages 정적 사이트. 서버 사이드 없음. 클라이언트 JS + `/data/*.json` fetch. 추가 서버 비용 0원 원칙.

---

## 2. 현재 코드 기준 상태 요약

| 항목 | 현재 구현 상태 (코드 근거) |
|------|---------------------------|
| 레이아웃 | 216px 고정 사이드바 + 2열 그리드 카드 (line 43, 92) |
| 카드 정보 | 기관배지 + 날짜 + 제목(2줄) + 요약(2줄) + 키워드(3개) + CTA 2개 (line 574) |
| 네비게이션 | 5개 분야 사이드바 필터 + 화살표 날짜 이동 (line 331–358) |
| 검색 | 제목/기관/요약 텍스트 인라인 필터 (line 537) |
| Top Picks | 키워드 수 기준 최대 3건, 스타일 인라인 (line 682–700) |
| 모바일 | 별도 헤더 + 6탭 카테고리 + 바텀 네비 5개 항목 (line 257–284, 182) |
| 개인화 | 없음 (읽음 상태 미추적, 관심분야 저장 없음) |
| 데이터 시각화 | 없음 (숫자 카운터만 존재) |
| 색상 위계 | 5색 카테고리 시스템 존재 (line 29: --c-fin, --c-soc 등) |

---

## 3. 벤치마크 분석 결과 및 개선사항

---

### [P0-1] Smart Brevity 카드 포맷 개선 — "3초 스캔" 구조

**벤치마크 출처:** Axios.com "Smart Brevity" 포맷 + Morning Brew 뉴스레터

**패턴 설명:**
Axios는 모든 기사를 "Why it matters"(1줄) → 본문 → "The bottom line"(1줄) 구조로 강제한다. Morning Brew는 굵은 핵심어를 앞에 두고 부드러운 설명을 이어붙인다. 공통점: 스캔 시 제목만으로 판단하지 않고, 제목 바로 아래 1줄 "임팩트 라인"을 배치해 클릭 전 판단을 돕는다.

**현재 govbrief.kr 상태:**
- `card-summary`: `font-size:12px`, 2줄 clamp, 키워드 하이라이트만 있음 (line 108–109)
- 요약 전체를 그대로 노출. "왜 중요한가"를 별도로 추출하지 않음
- 카드당 정보 밀도가 높아 3초 스캔이 어려움

**구체적 개선 제안:**

```css
/* 기존 card-summary 위에 임팩트 라인 추가 */
.card-impact {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.5;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  /* 카테고리 색상으로 좌측 보더 강조 */
  padding-left: 8px;
  border-left: 2px solid var(--card-color, var(--accent));
}

.card-summary {
  font-size: 11px; /* 기존 12px → 11px, 임팩트 라인과 위계 분리 */
  color: var(--text2);
  -webkit-line-clamp: 1; /* 기존 2줄 → 1줄로 축소 */
}
```

AI 파이프라인에서 요약 생성 시 첫 문장을 "핵심 행동/결정" 형태로 추출 (`briefingroom/app.py` 프롬프트 수정 필요). 프론트엔드에서는 `it.sum`의 첫 문장을 `.card-impact`에, 나머지를 `.card-summary`에 분리 표시.

**예상 효과:** 카드당 판단 소요 시간 3초 → 1.5초. CTR(상세 클릭률) 15~20% 향상 예상.

**우선순위: P0** (핵심 가치 제안 직결)

---

### [P0-2] 오늘의 브리핑 상단 고정 섹션 재설계

**벤치마크 출처:** The Skimm 뉴스레터 "Today's Rundown" + Politico.eu 상단 "Most Read" + Naver 뉴스 "헤드라인"

**패턴 설명:**
The Skimm은 페이지 최상단에 오늘의 핵심 3가지를 번호 리스트로 고정한다. Politico.eu는 "Top Stories" 수평 스크롤 카드를 메인 피드 위에 배치한다. Naver 뉴스는 이슈 클러스터링으로 관련 기사를 묶어 상단에 표시한다.

**현재 govbrief.kr 상태:**
- `#top-picks` 섹션 존재하나 `키워드 수` 기준 정렬이라 중요도 미반영 (line 686: `sort((a,b)=>b.kws.length-a.kws.length)`)
- 스타일이 인라인 `row.style.cssText`로 하드코딩되어 일관성 부족 (line 693)
- 최대 3건인데 카테고리 중복 방지 로직만 있고 실제 중요도 신호 없음
- "🔥 오늘의 핵심 보도자료" 레이블이 이모지 의존, 위계 표현 미흡

**구체적 개선 제안:**

```css
/* Top Picks 재설계 */
.top-picks-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.top-picks-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.top-picks-title {
  font-family: var(--serif);
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}

.top-picks-badge {
  font-family: var(--mono);
  font-size: 9px;
  color: var(--muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.top-pick-item {
  display: grid;
  grid-template-columns: 20px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}

.top-pick-item:last-child { border-bottom: none; }

.top-pick-num {
  font-family: var(--mono);
  font-size: 16px;
  font-weight: 700;
  color: var(--border2);
  line-height: 1;
}

.top-pick-item:hover .top-pick-num {
  color: var(--accent);
}
```

중요도 신호 개선: `kws.length` 대신 `(kws.length * 2) + (sum.length > 100 ? 1 : 0)` 가중치 적용. 또는 AI 파이프라인에서 `importance_score` 필드 추가 (1~5).

**예상 효과:** 첫 화면 진입 후 3초 내 오늘의 핵심 파악. 이탈률 감소.

**우선순위: P0**

---

### [P0-3] 모바일 카드 정보 밀도 조정 — 엄지 도달성

**벤치마크 출처:** Gov.uk Design System + Naver 뉴스 모바일 앱

**패턴 설명:**
Gov.uk는 최소 터치 타겟 44px, 카드 내 액션 버튼을 카드 하단이 아닌 전체 카드 tap으로 대체한다. Naver 뉴스 모바일은 썸네일 없이 텍스트만으로 카드를 구성하되, 제목을 2줄, 출처+시간을 1줄로 엄격히 제한한다.

**현재 govbrief.kr 상태:**
- 모바일에서 `.press-card .card-actions{display:none}` (line 220) — 버튼 숨김은 올바름
- 그러나 카드 클릭 → `openDetail()` 전체 카드 탭 작동 (line 588) — 올바름
- `card-title: font-size:14px; -webkit-line-clamp:2` (line 221) — 적정
- 문제: 카드 padding `14px 16px` (line 96). 모바일에서 카드 간 `gap:8px` (line 92). 화면당 카드 수가 2~3개에 그쳐 스크롤 효율 낮음
- `.card-summary` 모바일에서도 표시됨 — 카드 높이 증가 원인

**구체적 개선 제안:**

```css
/* 모바일 카드 컴팩트 모드 */
@media (max-width: 768px) {
  .press-card {
    padding: 12px 14px; /* 기존 14px 16px → 2px씩 축소 */
    border-radius: 8px; /* 기존 10px */
  }

  .cards-grid {
    gap: 6px; /* 기존 8px */
  }

  /* 모바일에서 요약 숨기고 키워드 태그만 표시 */
  .press-card .card-summary {
    display: none;
  }

  /* 키워드 태그를 카드 하단이 아닌 제목 바로 아래로 이동 */
  .card-meta {
    margin-top: 4px;
  }

  /* 카드 상단 기관 배지 + 시간을 한 줄로 */
  .card-top {
    margin-bottom: 5px;
  }
}
```

화면당 카드 수 현재 2~3개 → 개선 후 3~4개 목표. 스크롤당 정보 효율 30% 향상.

**예상 효과:** 모바일 사용자 스크롤 깊이(scroll depth) 증가, 이탈률 감소.

**우선순위: P0**

---

### [P1-1] 날짜 네비게이션 — 날짜 피커 + 주간 히트맵

**벤치마크 출처:** GovTrack.us 날짜 필터 + Feedly 타임라인 뷰

**패턴 설명:**
GovTrack은 기간 선택 시 달력 팝오버를 제공하며 날짜별 활동량을 점 크기로 표시한다. Feedly는 날짜별 기사 수를 미니 바차트로 타임라인에 시각화해 "많은 날"을 직관적으로 파악하게 한다.

**현재 govbrief.kr 상태:**
- 날짜 이동: 화살표 버튼만으로 1일 단위 이동 (line 47–48, 331–334)
- 현재 날짜 레이블: `YYYY-MM-DD` monospace 텍스트만 표시 (line 46)
- 빠른 날짜 점프 불가 — 3일 전 데이터 보려면 좌측 화살표 3번 클릭
- 주말 자동 주간 집계 로직은 있으나 (line 456–464) 사용자가 이를 인지 불가

**구체적 개선 제안:**

```html
<!-- 날짜 네비 영역 확장 -->
<div class="date-nav">
  <button class="date-arrow" onclick="changeDate(-1)">◀</button>
  <button class="date-nav-label" id="date-label" onclick="openDatePicker()"
    style="cursor:pointer; text-decoration: underline dotted; text-underline-offset: 2px">
  </button>
  <button class="date-arrow" onclick="changeDate(1)">▶</button>
</div>

<!-- 날짜 피커 드롭다운 (inline 방식, 서버 불필요) -->
<div id="date-picker" style="display:none; position:absolute; background:var(--surface);
  border:1px solid var(--border); border-radius:10px; padding:12px; z-index:20;
  box-shadow:0 8px 24px rgba(0,0,0,.12)">
  <!-- 최근 7일 버튼 목록 + 활동량 표시 -->
</div>
```

```javascript
function openDatePicker() {
  // 최근 14일의 데이터 파일 존재 여부를 HEAD 요청으로 확인 후
  // 날짜별 상대적 활동량을 도트 크기로 표시
  const recentDates = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    recentDates.push(d);
  }
  // 렌더링: 날짜 버튼 + 기사 수 표시
}
```

**예상 효과:** 날짜 이동 UX 마찰 감소. "지난 월요일" 같은 직접 이동 가능.

**우선순위: P1**

---

### [P1-2] 읽음 상태 + 로컬 북마크

**벤치마크 출처:** Feedly "Read Later" + Inoreader 읽음 표시 + TheyWorkForYou 알림

**패턴 설명:**
Feedly는 기사 카드에 읽음/안읽음 상태를 시각적으로 구분(흐림 처리)하고 "나중에 읽기" 아이콘을 카드 우상단에 배치한다. Inoreader는 스크롤을 내리면 자동으로 읽음 처리한다. TheyWorkForYou는 이전에 본 업데이트를 새 업데이트와 구분해 강조한다.

**현재 govbrief.kr 상태:**
- 읽음 상태 추적 전무 (코드 어디에도 localStorage 기반 read state 없음)
- 매일 새 데이터 로드 시 카드가 모두 동일하게 표시
- 재방문 사용자가 "어디까지 봤는지" 파악 불가

**구체적 개선 제안:**

```javascript
// localStorage 기반 읽음 상태 관리 (서버 불필요)
const READ_KEY = 'gbr_read_v1';

function getReadSet() {
  try {
    return new Set(JSON.parse(localStorage.getItem(READ_KEY) || '[]'));
  } catch { return new Set(); }
}

function markRead(id) {
  const s = getReadSet();
  s.add(id);
  // 최대 500개 유지 (오래된 것 삭제)
  const arr = [...s].slice(-500);
  localStorage.setItem(READ_KEY, JSON.stringify(arr));
}

function isRead(id) {
  return getReadSet().has(id);
}

// mkCard() 내에서 적용
// c.classList.toggle('read', isRead(it.id));
// openDetail() 내에서 markRead(it.id) 호출
```

```css
.press-card.read {
  opacity: 0.65;
}

.press-card.read .card-title {
  color: var(--text2);
}

/* 읽음 표시 점 */
.press-card.read::after {
  content: '✓';
  position: absolute;
  top: 8px;
  right: 10px;
  font-size: 10px;
  color: var(--muted);
  font-family: var(--mono);
}
```

**예상 효과:** 재방문자 체류 시간 증가. "안 읽은 것만 보기" 필터 연계 가능.

**우선순위: P1**

---

### [P1-3] 키워드 트렌드 바 — 오늘의 핫 키워드

**벤치마크 출처:** Naver 실시간 검색어 + Politico.eu "Trending Topics" + Feedly 태그 클라우드

**패턴 설명:**
Naver 뉴스는 상단에 실시간 트렌딩 키워드를 가로 스크롤로 표시한다. Politico.eu는 섹션 사이드바에 "Trending Topics" 링크 목록을 배치한다. Feedly는 가장 많이 등장한 태그를 크기 가중치로 태그 클라우드로 시각화한다.

**현재 govbrief.kr 상태:**
- `renderSourceBadges()` 함수로 기관별 카운트 배지를 표시하나 (line 701–710) 키워드 트렌드 없음
- 키워드는 각 카드 내 `kw-tag`로 분산 표시만 됨
- `allItems`에 `kws` 배열 존재 — 집계 인프라는 있음

**구체적 개선 제안:**

```javascript
function renderKeywordTrend() {
  // 전체 키워드 빈도 집계
  const kwCount = {};
  allItems.forEach(it => {
    (it.kws || []).forEach(k => {
      kwCount[k] = (kwCount[k] || 0) + 1;
    });
  });

  const top10 = Object.entries(kwCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  // 사이드바 하단 또는 top-picks 섹션 위에 렌더링
  const container = document.getElementById('kw-trend');
  container.innerHTML = top10.map(([kw, cnt], i) =>
    `<button class="kw-trend-btn" onclick="handleSearch('${escapeHtml(kw)}')"
      style="opacity:${1 - i * 0.07}">
      <span class="kw-trend-rank">${i + 1}</span>
      ${escapeHtml(kw)}
      <span class="kw-trend-cnt">${cnt}</span>
    </button>`
  ).join('');
}
```

```css
.kw-trend-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  border: none;
  background: none;
  cursor: pointer;
  font-family: var(--sans);
  font-size: 12px;
  color: var(--text2);
  width: 100%;
  text-align: left;
  transition: background .1s;
}

.kw-trend-btn:hover { background: var(--bg2); color: var(--accent); }

.kw-trend-rank {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted);
  min-width: 14px;
  font-weight: 700;
}

.kw-trend-cnt {
  margin-left: auto;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted);
  background: var(--bg2);
  padding: 1px 5px;
  border-radius: 4px;
}
```

배치: 데스크톱 사이드바 `#ministry-sb` 위, 또는 `.top-picks` 아래 가로 스크롤 배너.

**예상 효과:** 사용자가 필터 탐색 없이 오늘 주목 키워드 파악. 검색 유도.

**우선순위: P1**

---

### [P1-4] 카드 색상/타이포그래피 위계 강화

**벤치마크 출처:** Gov.uk Design System + Axios 카드 레이아웃

**패턴 설명:**
Gov.uk는 정보 위계를 색상이 아닌 크기/굵기/간격으로 전달한다. 색상은 보조 신호로만 사용. Axios는 제목을 18px bold, 본문을 14px regular로 명확히 구분하고 여백을 넉넉히 준다.

**현재 govbrief.kr 상태:**
- `card-title: font-size:13px; font-weight:500` (line 107) — 너무 작고 굵기 약함
- `card-summary: font-size:12px; color:var(--text2)` (line 108) — 제목과 크기 차이 1px만 차이
- `m-badge: font-size:10px` (line 105) — 기관명이 너무 작아 인지 부하
- 전체 배경 도트 패턴 (`body::before` line 33) — 텍스트 가독성 저해 가능성

**구체적 개선 제안:**

```css
/* 위계 강화 */
.card-title {
  font-size: 14px;      /* 기존 13px → 14px */
  font-weight: 600;     /* 기존 500 → 600 */
  line-height: 1.45;
  letter-spacing: -0.2px;
}

.card-summary {
  font-size: 12px;      /* 유지 */
  color: var(--text2);
  line-height: 1.6;
}

/* 기관 배지 크기 증가 — 출처 인지 강화 */
.m-badge {
  font-size: 11px;      /* 기존 10px → 11px */
  font-weight: 600;
  padding: 3px 9px;     /* 기존 2px 8px */
}

/* 도트 배경 불투명도 감소 */
body::before {
  opacity: 0.3;         /* 기존 0.5 → 0.3 */
}

/* 카드 간 구분을 보더보다 그림자로 */
.press-card {
  border: 1px solid var(--border);
  box-shadow: 0 1px 3px rgba(0,0,0,.04);  /* 미세 그림자 추가 */
}

.press-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,.09);
  border-color: var(--border2);
}
```

**예상 효과:** 가독성 개선. 기관 출처 인지율 향상. 정보 위계 명확화.

**우선순위: P1**

---

### [P2-1] 관심 분야 기억 — 개인화 필터 유지

**벤치마크 출처:** Feedly 관심 피드 구독 + Inoreader 폴더 관리

**패턴 설명:**
Feedly는 첫 방문 시 관심 분야(카테고리)를 선택하게 하고, 이후 방문 시 해당 필터가 기본 활성화된다. Inoreader는 폴더별 읽음/안읽음 카운트를 사이드바에 표시해 우선순위를 돕는다.

**현재 govbrief.kr 상태:**
- `curFilter='all'` 매 방문마다 초기화 (line 432)
- localStorage에 저장되는 상태: `cta_dismissed`, `hero_dismissed`만 존재 (line 636, 644)
- 사용자가 매번 같은 필터를 다시 선택해야 함

**구체적 개선 제안:**

```javascript
// 필터 상태 영속화
const FILTER_KEY = 'gbr_filter_pref';

function setFilter(cat, el) {
  curFilter = cat;
  localStorage.setItem(FILTER_KEY, cat); // 저장
  // ... 기존 로직
}

// 초기화 시 복원
(async () => {
  const savedFilter = localStorage.getItem(FILTER_KEY);
  // URL 파라미터가 없을 때만 저장된 필터 적용
  if (savedFilter && !catParam && !ministry) {
    curFilter = savedFilter;
  }
  await loadData();
  // ...
})();
```

**예상 효과:** 재방문 사용자 경험 개선. 매일 같은 분야를 보는 공무원/기자 타겟에 효과적.

**우선순위: P2**

---

### [P2-2] 카테고리별 건수 시각화 — 미니 바차트

**벤치마크 출처:** GovTrack 활동 히트맵 + Politico.eu 섹션 통계

**패턴 설명:**
GovTrack은 의원별 투표 참여율을 수평 바로 시각화한다. Politico.eu는 섹션 헤더에 "32 stories today" 같은 카운터 외 상대적 활동량을 보여준다.

**현재 govbrief.kr 상태:**
- `f-cnt` 요소로 숫자 카운트만 표시 (line 57)
- 5개 카테고리 간 상대적 비중 파악 불가 — 숫자만 보임
- 데이터는 `countsByCat` 객체에 이미 있음 (line 507)

**구체적 개선 제안:**

```javascript
function updateSidebarWithBars() {
  const total = allItems.length || 1;
  CO.forEach(cat => {
    const cnt = countsByCat[cat] || 0;
    const pct = Math.round((cnt / total) * 100);
    const barEl = document.getElementById(`bar-${cat}`);
    if (barEl) barEl.style.width = `${pct}%`;
  });
}
```

```html
<!-- 각 f-item 내 바 추가 -->
<div class="f-bar-wrap">
  <div class="f-bar" id="bar-금융경제" style="background:var(--c-fin)"></div>
</div>
```

```css
.f-bar-wrap {
  height: 2px;
  background: var(--border);
  border-radius: 1px;
  margin: 2px 8px 6px;
  overflow: hidden;
}

.f-bar {
  height: 100%;
  border-radius: 1px;
  transition: width .4s ease;
  opacity: 0.6;
}
```

**예상 효과:** 오늘 어느 분야 발표가 많은지 시각적으로 즉시 파악.

**우선순위: P2**

---

### [P2-3] 공유 기능 강화 — OG 이미지 + 딥링크

**벤치마크 출처:** Morning Brew 뉴스레터 공유 + Axios 기사 공유

**패턴 설명:**
Morning Brew는 각 기사에 소셜 공유 시 OG 이미지를 동적 생성(Cloudinary URL 파라미터 방식)한다. Axios는 기사 URL을 클립보드에 복사 시 "Copied!" 피드백을 애니메이션으로 즉시 표시한다.

**현재 govbrief.kr 상태:**
- `shareNative()`, `copyLink()` 함수 존재 (line 420–421)
- 공유 URL: `?date=...&article=...` (line 592) — 딥링크는 작동
- OG 이미지: `og:image` 메타태그 없음 (line 10–15 확인)
- 복사 후 피드백: `id="copy-btn"` 요소 있으나 상태 변경 코드 확인 필요

**구체적 개선 제안:**

```html
<!-- head에 동적 OG 이미지 추가 (Cloudinary 없이 정적 fallback) -->
<meta property="og:image" content="https://govbrief.kr/og-default.png">
<meta name="twitter:image" content="https://govbrief.kr/og-default.png">
```

```javascript
// copyLink() 피드백 개선
async function copyLink() {
  try {
    await navigator.clipboard.writeText(_shareUrl);
    const btn = document.getElementById('copy-btn');
    const original = btn.textContent;
    btn.textContent = '✓ 복사됨';
    btn.style.color = 'var(--c-soc)';
    btn.style.borderColor = 'var(--c-soc)';
    setTimeout(() => {
      btn.textContent = original;
      btn.style.color = '';
      btn.style.borderColor = '';
    }, 2000);
  } catch(e) {
    // fallback
  }
}
```

**예상 효과:** 소셜 공유 시 카드 미리보기 표시. 공유 UX 완성도 향상.

**우선순위: P2**

---

### [P2-4] 검색 UX 개선 — 즉시 하이라이트 + 결과 카운트

**벤치마크 출처:** GovTrack 검색 + Feedly 검색 결과

**패턴 설명:**
GovTrack은 검색 입력 즉시 결과 수를 인라인으로 표시하고, 매칭된 텍스트에 배경 하이라이트를 적용한다. Feedly는 검색 중 로딩 인디케이터를 표시하고 "No results for X" 메시지를 명확히 표시한다.

**현재 govbrief.kr 상태:**
- `handleSearch()` 실시간 필터링 작동 (line 537)
- `setHighlightedText()` 키워드 하이라이트 존재 (line 511–525)
- 검색 결과 수: `total-badge`에 표시되나 search 상태임을 시각적으로 구분 안 함
- 검색 중임을 나타내는 UI 피드백 없음

**구체적 개선 제안:**

```css
/* 검색 활성 상태 표시 */
.search-in.has-query {
  border-color: var(--accent);
  background: var(--accent-l);
}

/* 검색 결과 카운트 강조 */
.total-badge.search-active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
```

```javascript
function handleSearch(q) {
  curSearch = q.toLowerCase();
  expanded = {};
  // 검색 상태 시각 피드백
  const input = document.getElementById('search-in');
  const badge = document.getElementById('total-badge');
  if (q) {
    input?.classList.add('has-query');
    badge?.classList.add('search-active');
  } else {
    input?.classList.remove('has-query');
    badge?.classList.remove('search-active');
  }
  render();
}
```

**예상 효과:** 검색 상태 명확화. 사용자가 필터링 중임을 인지.

**우선순위: P2**

---

## 4. 우선순위 종합

### P0 — 즉시 구현 (이번 스프린트)

| ID | 개선사항 | 영향 범위 | 난이도 |
|----|----------|-----------|--------|
| P0-1 | Smart Brevity 카드 포맷 (임팩트 라인) | 모든 카드 | 낮음 (CSS + JS 10줄) |
| P0-2 | Top Picks 섹션 재설계 (중요도 신호) | 상단 섹션 | 낮음 (JS 30줄 + CSS) |
| P0-3 | 모바일 카드 컴팩트 (요약 숨김, padding 조정) | 모바일 전체 | 낮음 (CSS only) |

P0 3개 모두 GitHub Pages 정적 제약 내 순수 CSS/JS 변경. 서버 변경 불필요.

### P1 — 다음 스프린트 (1~2주)

| ID | 개선사항 | 영향 범위 | 난이도 |
|----|----------|-----------|--------|
| P1-1 | 날짜 피커 드롭다운 | 네비게이션 | 중간 (JS 50줄 + CSS) |
| P1-2 | 읽음 상태 + localStorage | 카드 전체 | 중간 (JS 40줄 + CSS) |
| P1-3 | 키워드 트렌드 바 (TOP 10) | 사이드바 | 낮음 (JS 20줄 + CSS) |
| P1-4 | 카드 타이포그래피 위계 강화 | 카드 전체 | 낮음 (CSS only) |

### P2 — 백로그 (추후 검토)

| ID | 개선사항 | 영향 범위 | 난이도 |
|----|----------|-----------|--------|
| P2-1 | 관심 분야 localStorage 기억 | 필터 상태 | 낮음 (JS 10줄) |
| P2-2 | 카테고리별 미니 바차트 | 사이드바 | 낮음 (JS 15줄 + CSS) |
| P2-3 | OG 이미지 + 복사 피드백 | 공유 기능 | 낮음 (HTML 2줄 + JS 10줄) |
| P2-4 | 검색 상태 시각 피드백 | 검색 UX | 낮음 (CSS + JS 10줄) |

---

## 5. 벤치마크 패턴 → govbrief.kr 적용 매핑 요약

| 벤치마크 서비스 | 채택한 패턴 | 적용 항목 |
|----------------|-------------|-----------|
| Axios Smart Brevity | 임팩트 라인 (제목 아래 1줄 핵심) | P0-1 |
| Morning Brew | 번호 리스트 브리핑 구조 | P0-2 |
| Gov.uk Design System | 44px 터치 타겟, 컴팩트 모바일 카드 | P0-3 |
| Naver 뉴스 모바일 | 텍스트 온리 카드, 모바일 정보 밀도 | P0-3 |
| GovTrack.us | 날짜 피커 + 활동량 시각화 | P1-1 |
| Feedly / Inoreader | 읽음 상태 추적, 나중에 읽기 | P1-2 |
| Naver 실시간 검색 + Politico 트렌딩 | 키워드 트렌드 TOP 10 | P1-3 |
| Gov.uk + Axios | 타이포그래피 위계 (크기/굵기) | P1-4 |
| Feedly 구독 관리 | 필터 상태 localStorage 기억 | P2-1 |
| GovTrack 활동 히트맵 | 카테고리별 미니 바차트 | P2-2 |
| Axios / Morning Brew 공유 | OG 이미지 + 복사 피드백 | P2-3 |
| GovTrack 검색 | 검색 상태 시각 피드백 | P2-4 |

---

## 6. 의도적으로 채택하지 않은 패턴 (Won't)

| 패턴 | 출처 | 미채택 이유 |
|------|------|-------------|
| 동적 OG 이미지 생성 | Morning Brew / Cloudinary | GitHub Pages 서버리스 제약. CDN 비용 발생 |
| 실시간 알림 (Push) | GovTrack / TheyWorkForYou | 서비스 워커 + 백엔드 필요. 텔레그램 채널로 대체 중 |
| AI 챗봇 Q&A | Politico.eu Pro | 서버 비용 + LLM API 비용. 수익화 이전 단계 |
| 인터랙티브 차트 | D3.js 기반 시각화 | 번들 크기 증가, 정적 사이트 제약 |
| 소셜 로그인 / 계정 | Feedly 계정 동기화 | 현재 스택에서 불가. Supabase 도입 전 보류 |
| 썸네일 이미지 | Daum 뉴스 카드 | 정부 보도자료에 고품질 이미지 없음. 텍스트가 핵심 자산 |

---

## 7. 성공 지표

| 지표 | 현재 (추정) | 목표 (P0 완료 후 4주) |
|------|------------|----------------------|
| 모바일 화면당 카드 노출 수 | 2~3개 | 3~4개 |
| Top Picks 클릭률 | 측정 불가 | 전체 클릭의 15%+ |
| 재방문자 필터 재설정 비율 | 100% | 30% 이하 (P2-1 완료 후) |
| 카드 상세 열람 전환율 | 측정 불가 | GA4 이벤트 추적 후 baseline 수립 |

---

## 8. 구현 노트

- 모든 P0/P1 변경은 `/Users/kyunghwansohn/Desktop/briefingroom_new/index.html` 단일 파일 수정
- CSS 변경 시 기존 `:root` 변수 체계 유지 필수 (line 29의 `--bg`, `--text` 등)
- JS 변경 시 기존 전역 변수 (`allItems`, `curFilter`, `curView`) 그대로 활용
- 모바일/데스크톱 분기는 `@media(max-width:768px)` 기준 유지
- P1-2 읽음 상태 key: `gbr_read_v1` (버전 관리 목적)
- P2-1 필터 기억 key: `gbr_filter_pref`

---

## 9. 다음 단계

1. CTO(팀 리드) Plan 검토 및 승인
2. P0 3개 항목 → `/Users/kyunghwansohn/Desktop/briefingroom_new/index.html` Do 단계 진입
3. 구현 완료 후 실제 모바일 기기 터치 테스트
4. GA4 이벤트 추가 후 전환율 baseline 수립 (Check 단계)
