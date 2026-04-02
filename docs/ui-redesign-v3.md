# govbrief.kr UI/UX 혁신 설계서 v3

작성일: 2026-03-29
대상: index.html (Vanilla JS + CSS, 정적 GitHub Pages)

---

## 목차

1. 디자인 시스템 v2
2. 데스크톱 레이아웃 혁신
3. 모바일웹 레이아웃 혁신
4. 새로운 UI 컴포넌트
5. 상세 페이지 리디자인
6. 인터랙션 & 애니메이션
7. 구현 전략 & 마이그레이션 계획

---

## 1. 디자인 시스템 v2

### 1-1. 색상 팔레트 방향성

현재 베이지(`#f5f4f0`) 기반은 "따뜻하지만 무게감 없음"이 문제입니다.
목표: **다크 프라이머리 + 콜드 액센트 + 뉴트럴 서피스** 조합으로 정보 신뢰성과 프리미엄감을 동시에 달성합니다.

벤치마크: Financial Times (연어색+검정), Bloomberg Terminal (고밀도 다크), Nikkei Asia (미니멀 흑백+강조색)

```css
:root {
  /* === Surface === */
  --bg:        #F8F7F4;   /* 메인 배경: 따뜻한 오프화이트 (현재 유지) */
  --bg2:       #F0EEE9;   /* 섹션 배경 */
  --bg3:       #E8E5DF;   /* 인풋/태그 배경 */
  --surface:   #FFFFFF;   /* 카드/모달 배경 */
  --surface2:  #FAFAF8;   /* 카드 hover 배경 */

  /* === Text === */
  --text:      #111110;   /* 메인 텍스트: 더 진하게 (현재 #1c1b18) */
  --text2:     #3D3B37;   /* 서브 텍스트 */
  --text3:     #6B6860;   /* 설명/레이블 */
  --muted:     #9C9893;   /* Placeholder/Disabled */

  /* === Border === */
  --border:    #E2DED8;   /* 기본 경계선 */
  --border2:   #C8C4BC;   /* 강조 경계선 */
  --border3:   #A8A49C;   /* 인터랙티브 경계선 */

  /* === Accent (프라이머리 액션) === */
  --accent:    #1A47CC;   /* 현재 #2f54eb 대비 더 깊고 신뢰감 있는 블루 */
  --accent-h:  #1238A8;   /* hover */
  --accent-l:  #EEF1FD;   /* 라이트 배경 */
  --accent-m:  rgba(26,71,204,0.12); /* 미디엄 배경 */

  /* === 카테고리 색상: 채도 대폭 절제 === */
  --c-fin:     #1A47CC;   /* 금융: 딥 블루 */
  --c-soc:     #0F6B3A;   /* 사회: 딥 그린 */
  --c-ind:     #9A4A0A;   /* 산업: 딥 앰버 */
  --c-dip:     #A31515;   /* 외교: 딥 레드 */
  --c-adm:     #5B20B8;   /* 행정: 딥 퍼플 */

  /* === 카테고리 라이트 배경 === */
  --c-fin-l:   #EEF1FD;
  --c-soc-l:   #ECFDF5;
  --c-ind-l:   #FFF7ED;
  --c-dip-l:   #FEF2F2;
  --c-adm-l:   #F5F3FF;

  /* === 시맨틱 === */
  --success:   #16A34A;
  --warning:   #D97706;
  --error:     #DC2626;
  --info:      --accent;

  /* === 타이포그래피 === */
  --serif:     'Noto Serif KR', serif;
  --sans:      'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
  --mono:      'DM Mono', 'Fira Code', monospace;

  /* === 스페이싱 (4px 그리드) === */
  --sp-1:  4px;
  --sp-2:  8px;
  --sp-3:  12px;
  --sp-4:  16px;
  --sp-5:  20px;
  --sp-6:  24px;
  --sp-8:  32px;
  --sp-10: 40px;
  --sp-12: 48px;
  --sp-16: 64px;

  /* === Border Radius === */
  --r-sm:  6px;
  --r-md:  10px;
  --r-lg:  14px;
  --r-xl:  20px;
  --r-2xl: 28px;

  /* === 그림자/엘리베이션 === */
  --shadow-0: none;
  --shadow-1: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-2: 0 2px 8px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-3: 0 4px 16px rgba(0,0,0,0.10), 0 2px 4px rgba(0,0,0,0.06);
  --shadow-4: 0 8px 32px rgba(0,0,0,0.14), 0 4px 8px rgba(0,0,0,0.08);
  --shadow-5: 0 20px 60px rgba(0,0,0,0.20), 0 8px 20px rgba(0,0,0,0.10);

  /* 모달/바텀시트 전용 - 색조 있는 그림자 */
  --shadow-modal: 0 24px 72px rgba(17,17,16,0.22), 0 8px 24px rgba(17,17,16,0.10);

  /* === 트랜지션 === */
  --t-fast:   80ms cubic-bezier(0.4, 0, 0.2, 1);
  --t-base:   150ms cubic-bezier(0.4, 0, 0.2, 1);
  --t-slow:   250ms cubic-bezier(0.4, 0, 0.2, 1);
  --t-spring: 300ms cubic-bezier(0.34, 1.56, 0.64, 1); /* 탄성 */

  /* === 모바일 치수 === */
  --mob-h:    52px;   /* 헤더 (현재 48px → 4px 증가, 여유 확보) */
  --mob-tab:  48px;   /* 카테고리 탭 */
  --mob-nav:  64px;   /* 바텀 네비 */
  --mob-safe: env(safe-area-inset-bottom, 0px);
}
```

### 1-2. 타이포그래피 스케일

```css
/* === 타입 스케일 (1.250 Major Third 비율) === */
:root {
  --text-2xs: 10px;   /* 타임스탬프, 카운트 배지 */
  --text-xs:  11px;   /* 메타 레이블, 모노 태그 */
  --text-sm:  12px;   /* 서브 텍스트, 캡션 */
  --text-base:14px;   /* 기본 본문 */
  --text-md:  15px;   /* 카드 제목 */
  --text-lg:  16px;   /* 섹션 헤딩 소 */
  --text-xl:  18px;   /* 섹션 헤딩 */
  --text-2xl: 20px;   /* 페이지 타이틀 */
  --text-3xl: 24px;   /* 상세 타이틀 */
  --text-4xl: 30px;   /* 히어로 타이틀 */
}

/* 카드 제목: 서체 위계 강화 */
.card-title {
  font-size: var(--text-md);
  font-weight: 700;
  line-height: 1.45;
  letter-spacing: -0.3px;
  color: var(--text);
}

/* 카드 요약: 본문 가독성 우선 */
.card-summary {
  font-size: var(--text-sm);
  font-weight: 400;
  line-height: 1.65;
  color: var(--text2);
}

/* 메타/배지: Mono 유지, 크기 통일 */
.m-badge, .card-time, .kw-tag {
  font-family: var(--mono);
  font-size: var(--text-xs);
}

/* 상세 타이틀: Serif + 큰 크기로 몰입감 */
.d-title {
  font-family: var(--serif);
  font-size: var(--text-3xl);
  font-weight: 700;
  line-height: 1.38;
  letter-spacing: -0.6px;
}
```

### 1-3. 아이콘 시스템

현재 이모지 아이콘의 문제: 플랫폼별 렌더링 불일치, 크기 조절 불가, 접근성 미흡.

**권장: Phosphor Icons (MIT, 경량 SVG 스프라이트)**

```html
<!-- head에 추가 (6KB gzip) -->
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/index.js"></script>

<!-- 사용 예시 -->
<i class="ph ph-magnifying-glass"></i>   <!-- 검색 -->
<i class="ph ph-funnel"></i>             <!-- 필터 -->
<i class="ph ph-calendar-blank"></i>    <!-- 날짜 -->
<i class="ph ph-buildings"></i>         <!-- 부처 -->
<i class="ph ph-paper-plane-tilt"></i>  <!-- 텔레그램 -->
<i class="ph ph-arrow-square-out"></i>  <!-- 원문 링크 -->
<i class="ph ph-share-network"></i>     <!-- 공유 -->
<i class="ph ph-link"></i>              <!-- 복사 -->
<i class="ph ph-x"></i>                 <!-- 닫기 -->
<i class="ph ph-caret-left"></i>        <!-- 이전 -->
<i class="ph ph-caret-right"></i>       <!-- 다음 -->
<i class="ph ph-squares-four"></i>      <!-- 그리드 뷰 -->
<i class="ph ph-list"></i>              <!-- 리스트 뷰 -->
<i class="ph ph-bookmark"></i>          <!-- 북마크 -->
<i class="ph ph-house"></i>             <!-- 홈 -->
```

```css
/* Phosphor 기본 설정 */
.ph { font-size: 16px; line-height: 1; }
.ph-sm { font-size: 14px; }
.ph-lg { font-size: 20px; }
.ph-xl { font-size: 24px; }
```

### 1-4. 마이크로 인터랙션 CSS

```css
/* ===== 마이크로 인터랙션 전역 규칙 ===== */

/* 모든 인터랙티브 요소: 가속도 커브 통일 */
button, a, [role="button"], .press-card {
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}

/* 카드 hover: scale 없이 shadow + border만 변화 */
.press-card {
  transition:
    border-color var(--t-base),
    box-shadow var(--t-base),
    background-color var(--t-fast);
}
.press-card:hover {
  border-color: var(--border2);
  box-shadow: var(--shadow-2);
  background-color: var(--surface2);
}
.press-card:active {
  background-color: var(--bg2);
  box-shadow: var(--shadow-1);
}

/* 버튼 press: scale 미세 축소 */
.btn-press:active { transform: scale(0.97); }

/* 링크/버튼: underline 애니메이션 */
.link-underline {
  position: relative;
}
.link-underline::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 0;
  height: 1px;
  background: currentColor;
  transition: width var(--t-base);
}
.link-underline:hover::after { width: 100%; }

/* 탭 인디케이터: 슬라이딩 언더라인 */
.tab-indicator {
  position: absolute;
  bottom: 0;
  height: 2px;
  background: var(--accent);
  border-radius: 2px 2px 0 0;
  transition: left var(--t-spring), width var(--t-spring);
}

/* 토글/체크박스: 상태 전환 */
.toggle-on { color: var(--accent); }
.toggle-off { color: var(--muted); }

/* 숫자 카운트 변경 시 flip 애니메이션 */
@keyframes countFlip {
  from { transform: translateY(-8px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
.count-updated { animation: countFlip 0.2s var(--t-base); }

/* 로딩 shimmer */
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg2) 25%,
    var(--bg3) 50%,
    var(--bg2) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.6s ease-in-out infinite;
  border-radius: var(--r-sm);
}
```

---

## 2. 데스크톱 레이아웃 혁신

### 2-1. 현재 구조의 한계

| 문제 | 영향 |
|------|------|
| 사이드바 216px 고정 → 메인이 협소 | 카드 2컬럼 그리드가 답답함 |
| 사이드바에 날짜 + 필터 혼재 | 정보 구조 불명확 |
| 상단바가 topbar + content에 분리 | 높이 낭비 |
| 100건을 2컬럼 단순 나열 | 중요도 차등 없음 |
| 상세가 작은 모달 | 긴 요약 읽기 불편 |

### 2-2. 레이아웃 선택 비교

**옵션 A: 강화된 사이드바 + 매거진 그리드 (권장)**
- 사이드바 240px (현재와 유사)
- 메인 영역: 상단에 "오늘의 핵심" 헤더 카드 + 하단 매거진 그리드
- 카테고리별 섹션 명확히 구분
- 장점: 현재 구조 유지 → 마이그레이션 비용 최소

**옵션 B: 3-패널 레이아웃**
- 왼쪽 240px 필터 + 중앙 480px 피드 + 오른쪽 340px 상세 패널
- 상세 클릭 시 오른쪽 패널에 표시 (모달 불필요)
- 장점: 뉴스룸 느낌, 상세 읽기 최적
- 단점: 구조 변경 대규모, 중앙 피드가 좁음

**옵션 C: 풀와이드 매거진 (사이드바 제거)**
- 헤더에 필터 수평 배치
- 전체 너비 활용한 매거진 레이아웃
- 장점: 가장 현대적
- 단점: 부처 목록 표시 공간 부족

**결론: 옵션 A** — 현재 코드베이스와의 호환성 + 정보 구조 명확성

### 2-3. 새로운 데스크톱 레이아웃 HTML/CSS

```html
<!-- 새 레이아웃 구조 -->
<div class="body-wrap">

  <!-- 사이드바: 240px, 3섹션 명확히 분리 -->
  <aside class="sidebar" aria-label="필터 및 탐색">

    <!-- S1: 날짜 네비게이션 -->
    <section class="sb-date">
      <div class="date-nav-v2">
        <button class="date-arrow-v2" onclick="changeDate(-1)" aria-label="전날">
          <i class="ph ph-caret-left"></i>
        </button>
        <div class="date-nav-center">
          <span class="date-nav-label" id="date-label"></span>
          <span class="date-nav-sub" id="date-nav-dow"></span>
        </div>
        <button class="date-arrow-v2" onclick="changeDate(1)" aria-label="다음날">
          <i class="ph ph-caret-right"></i>
        </button>
      </div>
    </section>

    <!-- S2: 분야 필터 -->
    <section class="sb-filters">
      <div class="sb-section-label">분야</div>
      <!-- 필터 아이템들 -->
    </section>

    <!-- S3: 부처 필터 (스크롤) -->
    <section class="sb-ministries">
      <div class="sb-section-label">
        <span>부처별</span>
        <span class="sb-search-mini">
          <i class="ph ph-magnifying-glass ph-sm"></i>
          <input type="text" placeholder="부처 검색" id="ministry-search">
        </span>
      </div>
      <div id="ministry-sb"></div>
    </section>

  </aside>

  <main class="main">

    <!-- 새 topbar: 검색 + 뷰전환 + 날짜 정보 -->
    <div class="topbar-v2">
      <div class="topbar-left">
        <h1 class="topbar-title" id="page-title">보도자료</h1>
        <span class="topbar-meta" id="page-sub"></span>
      </div>
      <div class="topbar-right">
        <div class="search-wrap-v2">
          <i class="ph ph-magnifying-glass search-ico"></i>
          <input class="search-in-v2" type="text" placeholder="검색..." id="search-in">
          <kbd class="search-kbd">/</kbd>
        </div>
        <div class="view-toggle-v2">
          <button class="v-btn" onclick="setView('grid',this)" aria-label="그리드">
            <i class="ph ph-squares-four"></i>
          </button>
          <button class="v-btn" onclick="setView('list',this)" aria-label="목록">
            <i class="ph ph-list"></i>
          </button>
        </div>
        <span class="total-badge-v2" id="total-badge">0건</span>
      </div>
    </div>

    <div class="content" id="main-content-wrap">
      <!-- "오늘의 핵심" 영역 (데스크톱 전용) -->
      <div class="daily-hero" id="daily-hero"></div>

      <!-- 보도자료 피드 -->
      <div id="main-content"></div>
    </div>

  </main>

</div>
```

```css
/* ===== 데스크톱 레이아웃 v2 ===== */

/* 사이드바 */
.sidebar {
  position: fixed;
  top: 56px;
  left: 0;
  width: 240px;
  height: calc(100vh - 56px);
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  z-index: 8;
  overflow: hidden; /* 섹션별 스크롤 */
}

/* 날짜 섹션: 압축적이지만 명확 */
.sb-date {
  padding: var(--sp-3) var(--sp-3);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.date-nav-v2 {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--sp-2) var(--sp-2);
  gap: var(--sp-2);
}

.date-nav-center {
  flex: 1;
  text-align: center;
}

.date-nav-label {
  font-family: var(--mono);
  font-size: var(--text-xs);
  color: var(--text2);
  font-weight: 500;
  display: block;
}

.date-nav-sub {
  font-family: var(--mono);
  font-size: var(--text-2xs);
  color: var(--muted);
  display: block;
  margin-top: 1px;
}

.date-arrow-v2 {
  width: 28px;
  height: 28px;
  border-radius: var(--r-sm);
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text3);
  display: grid;
  place-items: center;
  transition: background var(--t-fast), color var(--t-fast);
}

.date-arrow-v2:hover {
  background: var(--bg2);
  color: var(--text);
}

/* 분야 필터 섹션 */
.sb-filters {
  padding: var(--sp-2) var(--sp-2);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

/* 부처 섹션: flex:1로 남은 공간 채우고 스크롤 */
.sb-ministries {
  flex: 1;
  overflow-y: auto;
  padding: var(--sp-2) var(--sp-2);
  overscroll-behavior: contain;
}

.sb-section-label {
  font-family: var(--mono);
  font-size: var(--text-2xs);
  color: var(--muted);
  letter-spacing: 1.2px;
  text-transform: uppercase;
  padding: 0 var(--sp-2);
  margin-bottom: var(--sp-2);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 부처 검색 미니 인풋 */
.sb-search-mini {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 2px 6px;
}

.sb-search-mini input {
  background: none;
  border: none;
  outline: none;
  font-family: var(--sans);
  font-size: var(--text-2xs);
  color: var(--text);
  width: 80px;
}

/* 메인 영역 */
.main {
  margin-left: 240px;
  flex: 1;
  min-height: calc(100vh - 56px);
  max-width: calc(100vw - 240px);
  overflow-x: hidden;
}

/* Topbar v2: 더 컴팩트하고 정보 명확 */
.topbar-v2 {
  position: sticky;
  top: 56px;
  z-index: 5;
  background: rgba(248, 247, 244, 0.94);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 0 var(--sp-6);
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
}

.topbar-left {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
  min-width: 0;
}

.topbar-title {
  font-family: var(--serif);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.4px;
  color: var(--text);
  white-space: nowrap;
}

.topbar-meta {
  font-family: var(--mono);
  font-size: var(--text-xs);
  color: var(--muted);
  white-space: nowrap;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-shrink: 0;
}

/* 검색 v2: 키보드 단축키 표시 */
.search-wrap-v2 {
  position: relative;
  display: flex;
  align-items: center;
}

.search-ico {
  position: absolute;
  left: 10px;
  color: var(--muted);
  pointer-events: none;
  font-size: 13px;
}

.search-in-v2 {
  width: 220px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 6px 32px 6px 30px;
  font-family: var(--mono);
  font-size: var(--text-xs);
  color: var(--text);
  outline: none;
  transition: border-color var(--t-base), box-shadow var(--t-base), width var(--t-slow);
}

.search-in-v2::placeholder { color: var(--muted); }

.search-in-v2:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-m);
  width: 280px;
}

.search-kbd {
  position: absolute;
  right: 8px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted);
  pointer-events: none;
  transition: opacity var(--t-base);
}

.search-in-v2:focus + .search-kbd { opacity: 0; }

/* 뷰 토글 v2 */
.view-toggle-v2 {
  display: flex;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  overflow: hidden;
}

.view-toggle-v2 .v-btn {
  padding: var(--sp-2) var(--sp-3);
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  font-size: 14px;
  transition: background var(--t-fast), color var(--t-fast);
}

.view-toggle-v2 .v-btn.active {
  background: var(--text);
  color: #fff;
}

/* 총 건수 배지 v2 */
.total-badge-v2 {
  font-family: var(--mono);
  font-size: var(--text-xs);
  color: var(--accent);
  background: var(--accent-l);
  border: 1px solid var(--accent-m);
  padding: var(--sp-1) var(--sp-3);
  border-radius: 20px;
  white-space: nowrap;
}

/* 콘텐츠 패딩 */
.content {
  padding: var(--sp-6);
}

/* 카드 그리드 v2: 균등 3컬럼도 지원 */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--sp-3);
}

@media (min-width: 1400px) {
  .sidebar { width: 256px; }
  .main { margin-left: 256px; max-width: calc(100vw - 256px); }
  .cards-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (min-width: 769px) and (max-width: 1100px) {
  .sidebar { width: 200px; }
  .main { margin-left: 200px; max-width: calc(100vw - 200px); }
  .topbar-v2 { padding: 0 var(--sp-4); }
  .search-in-v2 { width: 160px; }
  .search-in-v2:focus { width: 200px; }
}
```

### 2-4. "오늘의 핵심" 데스크톱 히어로 영역

```css
/* 데스크톱 전용: 오늘의 핵심 (상위 3건 하이라이트) */
.daily-hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: var(--sp-3);
  margin-bottom: var(--sp-6);
}

.hero-main {
  grid-column: 1;
  grid-row: 1 / 3;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: var(--sp-6);
  cursor: pointer;
  transition: box-shadow var(--t-base), border-color var(--t-base);
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  position: relative;
  overflow: hidden;
}

.hero-main::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--hero-accent, var(--accent));
  border-radius: var(--r-lg) var(--r-lg) 0 0;
}

.hero-main:hover {
  box-shadow: var(--shadow-3);
  border-color: var(--border2);
}

.hero-label {
  font-family: var(--mono);
  font-size: var(--text-2xs);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.hero-label::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--hero-accent, var(--accent));
}

.hero-title {
  font-family: var(--serif);
  font-size: var(--text-xl);
  font-weight: 700;
  line-height: 1.42;
  letter-spacing: -0.5px;
  color: var(--text);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hero-summary {
  font-size: var(--text-sm);
  color: var(--text2);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.hero-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
}

.hero-badge {
  font-family: var(--mono);
  font-size: var(--text-xs);
  padding: 3px 8px;
  border-radius: var(--r-sm);
  background: var(--hero-bg, var(--accent-l));
  color: var(--hero-accent, var(--accent));
}

/* 서브 히어로 카드 (오른쪽 2개) */
.hero-sub {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--sp-4) var(--sp-5);
  cursor: pointer;
  transition: box-shadow var(--t-base), border-color var(--t-base);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  position: relative;
}

.hero-sub::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--hero-accent, var(--accent));
  border-radius: var(--r-md) 0 0 var(--r-md);
}

.hero-sub:hover {
  box-shadow: var(--shadow-2);
  border-color: var(--border2);
}

.hero-sub .hero-title {
  font-size: var(--text-md);
  -webkit-line-clamp: 2;
}

.hero-sub .hero-summary {
  -webkit-line-clamp: 2;
  font-size: var(--text-xs);
}
```

---

## 3. 모바일웹 레이아웃 혁신

### 3-1. 현재 모바일의 한계

| 문제 | 영향 |
|------|------|
| 헤더 + 탭바 + 콘텐츠 3단 스택 | 실제 콘텐츠 공간이 좁음 |
| 바텀네비 5탭 + 카테고리탭 중복 | 필터 UX 혼란 |
| 카드에 "상세보기"/"원문" 버튼 표시 | 불필요한 시각적 소음 |
| 상세가 풀스크린 바텀시트 | 읽기 중 컨텍스트 상실 |
| 제스처 없음 | 현대 모바일 UX와 괴리 |

### 3-2. 개선 방향

```
[현재]                    [개선]
헤더(48px)               헤더(52px) — 슬림하지만 여유
탭바(44px)               스크롤 시 탭바 자동 은닉 + 하단 네비로 통합
콘텐츠                   콘텐츠 최대화 (안전영역만 제외)
바텀네비(64px)           바텀네비 — 필터 탭 통합
```

```css
/* ===== 모바일 헤더 v2 ===== */
.m-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--mob-h); /* 52px */
  z-index: 50;
  background: rgba(248, 247, 244, 0.97);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  padding: 0 var(--sp-3);
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  /* 스크롤 숨김 준비 */
  transition: transform var(--t-slow);
}

/* 스크롤 다운 시 헤더 숨기기 (JS로 .hide 토글) */
.m-header.hide {
  transform: translateY(-100%);
}

/* ===== 카테고리 탭 v2: 헤더 바로 아래 ===== */
.m-cat-tabs-v2 {
  position: fixed;
  top: var(--mob-h);
  left: 0;
  right: 0;
  height: var(--mob-tab); /* 48px */
  z-index: 40;
  background: rgba(248, 247, 244, 0.97);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  display: flex;
  overflow-x: auto;
  scrollbar-width: none;
  padding: 0 var(--sp-3);
  gap: var(--sp-1);
  align-items: center;
  transition: transform var(--t-slow);
}

.m-cat-tabs-v2.hide {
  transform: translateY(calc(-1 * var(--mob-h) - 100%));
}

.m-cat-tabs-v2::-webkit-scrollbar { display: none; }

/* 탭 칩 스타일: 현재 텍스트+밑줄 → 필 칩 */
.m-tab-chip {
  flex-shrink: 0;
  height: 32px;
  padding: 0 var(--sp-3);
  border-radius: 20px;
  border: 1.5px solid var(--border);
  background: var(--surface);
  font-family: var(--sans);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text2);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  transition:
    background var(--t-base),
    border-color var(--t-base),
    color var(--t-base);
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  white-space: nowrap;
}

.m-tab-chip .m-tab-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.m-tab-chip.active {
  background: var(--text);
  border-color: var(--text);
  color: #fff;
}

.m-tab-chip.active .m-tab-dot {
  background: #fff !important;
}

/* ===== 카드 v2: 모바일 최적화 ===== */
.press-card-mobile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--sp-4) var(--sp-4);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  transition: background var(--t-fast);
  animation: fadeUp 0.22s ease both;
  /* 버튼 제거: 카드 자체가 탭 타겟 */
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}

.press-card-mobile:active {
  background: var(--bg2);
}

/* 카드 상단: 배지 + 날짜 인라인 */
.card-top-v2 {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 카드 제목: 2줄 클램프 */
.card-title-v2 {
  font-size: var(--text-md); /* 15px */
  font-weight: 700;
  line-height: 1.45;
  letter-spacing: -0.3px;
  color: var(--text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
}

/* 카드 요약: 1줄만 (간략 미리보기) */
.card-summary-v2 {
  font-size: var(--text-sm);
  color: var(--text2);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 키워드: 첫 2개만 */
.card-kws-v2 {
  display: flex;
  gap: var(--sp-1);
  flex-wrap: nowrap;
  overflow: hidden;
}

.kw-chip {
  font-family: var(--mono);
  font-size: var(--text-xs);
  color: var(--text3);
  background: var(--bg2);
  border: 1px solid var(--border);
  padding: 2px 7px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ===== 바텀 네비 v2: 더 명확한 계층 ===== */
.m-bottom-nav-v2 {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: calc(64px + var(--mob-safe));
  padding-bottom: var(--mob-safe);
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid var(--border);
  box-shadow: 0 -1px 0 var(--border), 0 -4px 20px rgba(0,0,0,0.06);
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  align-items: center;
  z-index: 50;
}

.m-nav-item-v2 {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 64px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  transition: color var(--t-fast);
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  text-decoration: none;
}

.m-nav-item-v2.active { color: var(--accent); }
.m-nav-item-v2 .ph { font-size: 22px; }
.m-nav-label-v2 {
  font-family: var(--sans);
  font-size: var(--text-2xs);
  font-weight: 600;
  letter-spacing: -0.2px;
}

/* 활성 탭 표시: 원형 필 배경 */
.m-nav-item-v2.active .ph {
  color: var(--accent);
}

/* 중앙 버튼 (날짜): 강조 스타일 */
.m-nav-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 64px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.m-nav-center-pill {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px 10px;
}

.m-nav-center-date {
  font-family: var(--mono);
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--text);
}
```

### 3-3. 스와이프 제스처 구현

```javascript
// 상세 패널 스와이프 다운으로 닫기
function initSwipeToClose(el) {
  let startY = 0, curY = 0, isDragging = false;

  el.addEventListener('touchstart', e => {
    // 상단에서만 드래그 시작 (핸들 영역)
    if (el.scrollTop > 10) return;
    startY = e.touches[0].clientY;
    isDragging = true;
    el.style.transition = 'none';
  }, { passive: true });

  el.addEventListener('touchmove', e => {
    if (!isDragging) return;
    curY = e.touches[0].clientY;
    const diff = curY - startY;
    if (diff > 0) {
      el.style.transform = `translateY(${diff}px)`;
    }
  }, { passive: true });

  el.addEventListener('touchend', () => {
    if (!isDragging) return;
    isDragging = false;
    const diff = curY - startY;
    el.style.transition = 'transform var(--t-slow)';

    if (diff > 120) {
      closeDetail();
    } else {
      el.style.transform = '';
    }
    startY = 0; curY = 0;
  });
}

// 카드 리스트 수평 스와이프 → 날짜 변경
function initDateSwipe(el) {
  let startX = 0, startTime = 0;

  el.addEventListener('touchstart', e => {
    startX = e.touches[0].clientX;
    startTime = Date.now();
  }, { passive: true });

  el.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - startX;
    const dt = Date.now() - startTime;

    // 빠른 스와이프만 (150ms 이내, 80px 이상)
    if (dt < 150 && Math.abs(dx) > 80) {
      if (dx < 0) changeDate(1);   // 왼쪽 → 다음날
      else        changeDate(-1);  // 오른쪽 → 전날
    }
  }, { passive: true });
}

// 스크롤 방향 감지 → 헤더/탭 은닉
(function initScrollHide() {
  let lastY = 0;
  const header = document.querySelector('.m-header');
  const tabs = document.querySelector('.m-cat-tabs-v2');

  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    const dy = y - lastY;
    lastY = y;

    if (y < 60) {
      header?.classList.remove('hide');
      tabs?.classList.remove('hide');
      return;
    }

    if (dy > 4) {
      header?.classList.add('hide');
      tabs?.classList.add('hide');
    } else if (dy < -4) {
      header?.classList.remove('hide');
      tabs?.classList.remove('hide');
    }
  }, { passive: true });
})();
```

---

## 4. 새로운 UI 컴포넌트

### 4-1. 카테고리 오버뷰 카드 (데스크톱 사이드바 하단 / 모바일 홈 상단)

```javascript
function renderCategoryOverview() {
  const container = document.getElementById('cat-overview');
  if (!container) return;

  const total = allItems.length;
  const html = CO.map(cat => {
    const cnt = countsByCat[cat] || 0;
    const pct = total ? Math.round(cnt / total * 100) : 0;
    const col = CC[cat] || '#1A47CC';
    return `
      <div class="cat-overview-item" onclick="setFilter('${cat}', this)"
           style="--cat-col:${col}">
        <div class="cat-ov-dot" style="background:${col}"></div>
        <span class="cat-ov-name">${CN[cat] || cat}</span>
        <div class="cat-ov-bar">
          <div class="cat-ov-fill" style="width:${pct}%;background:${col}"></div>
        </div>
        <span class="cat-ov-cnt">${cnt}</span>
      </div>
    `;
  }).join('');

  container.innerHTML = html;
}
```

```css
.cat-overview {
  padding: var(--sp-2) var(--sp-2);
}

.cat-overview-item {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 5px var(--sp-2);
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: background var(--t-fast);
}

.cat-overview-item:hover { background: var(--bg); }

.cat-ov-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.cat-ov-name {
  font-size: var(--text-xs);
  color: var(--text2);
  width: 60px;
  flex-shrink: 0;
}

.cat-ov-bar {
  flex: 1;
  height: 3px;
  background: var(--bg2);
  border-radius: 2px;
  overflow: hidden;
}

.cat-ov-fill {
  height: 100%;
  border-radius: 2px;
  transition: width var(--t-slow);
}

.cat-ov-cnt {
  font-family: var(--mono);
  font-size: var(--text-2xs);
  color: var(--muted);
  width: 24px;
  text-align: right;
  flex-shrink: 0;
}
```

### 4-2. 타임라인 뷰

```javascript
function renderTimeline(items) {
  // 시간대별 그룹핑 (오전/오후/저녁)
  const groups = { '오전': [], '오후': [], '저녁/야간': [] };
  items.forEach(it => {
    const hour = it.date ? parseInt(it.date.split(':')[0] || '0') : 0;
    if (hour < 12)  groups['오전'].push(it);
    else if (hour < 18) groups['오후'].push(it);
    else groups['저녁/야간'].push(it);
  });

  return Object.entries(groups)
    .filter(([, arr]) => arr.length)
    .map(([label, arr]) => `
      <div class="timeline-group">
        <div class="timeline-label">
          <span class="timeline-label-text">${label}</span>
          <span class="timeline-label-cnt">${arr.length}건</span>
        </div>
        <div class="timeline-items">
          ${arr.map(it => mkTimelineCard(it)).join('')}
        </div>
      </div>
    `).join('');
}
```

```css
.timeline-group {
  position: relative;
  padding-left: var(--sp-8);
  margin-bottom: var(--sp-6);
}

/* 타임라인 세로 선 */
.timeline-group::before {
  content: '';
  position: absolute;
  left: 14px;
  top: 28px;
  bottom: 0;
  width: 1px;
  background: var(--border);
}

.timeline-label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-3);
  position: relative;
}

/* 타임라인 점 */
.timeline-label::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--sp-8) + 10px);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--border2);
  border: 2px solid var(--surface);
  box-shadow: 0 0 0 1px var(--border2);
}

.timeline-label-text {
  font-family: var(--mono);
  font-size: var(--text-xs);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.timeline-label-cnt {
  font-family: var(--mono);
  font-size: var(--text-2xs);
  color: var(--muted);
  background: var(--bg2);
  padding: 1px 6px;
  border-radius: 10px;
}

.timeline-items {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}
```

### 4-3. 키워드 빈도 차트 (인라인 SVG, 라이브러리 불필요)

```javascript
function renderKeywordChart(items, container) {
  // 키워드 빈도 집계
  const freq = {};
  items.forEach(it => {
    (it.kws || []).forEach(k => {
      freq[k] = (freq[k] || 0) + 1;
    });
  });

  const top10 = Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  if (!top10.length) return;

  const max = top10[0][1];
  const BAR_MAX_W = 140;

  const rows = top10.map(([kw, cnt], i) => {
    const barW = Math.round(cnt / max * BAR_MAX_W);
    const opacity = 1 - i * 0.07;
    return `
      <g transform="translate(0, ${i * 28})">
        <text x="0" y="16" font-family="DM Mono, monospace"
              font-size="11" fill="var(--text2)">${kw}</text>
        <rect x="90" y="5" width="${barW}" height="14"
              rx="3" fill="var(--accent)" opacity="${opacity}"/>
        <text x="${90 + barW + 5}" y="16" font-family="DM Mono, monospace"
              font-size="10" fill="var(--muted)">${cnt}</text>
      </g>
    `;
  }).join('');

  container.innerHTML = `
    <div class="kw-chart-wrap">
      <div class="kw-chart-title">
        <span class="d-sec-label">키워드 트렌드</span>
      </div>
      <svg width="100%" viewBox="0 0 280 ${top10.length * 28}"
           xmlns="http://www.w3.org/2000/svg" role="img"
           aria-label="키워드 빈도 차트">
        ${rows}
      </svg>
    </div>
  `;
}
```

```css
.kw-chart-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--sp-4) var(--sp-5);
  margin-bottom: var(--sp-4);
}
```

### 4-4. 주간 하이라이트 섹션 (현재 special-block 개선)

```css
.weekly-highlight {
  background: linear-gradient(135deg, #0A1628 0%, #1A47CC 100%);
  border-radius: var(--r-lg);
  padding: var(--sp-5) var(--sp-6);
  margin-bottom: var(--sp-5);
  color: #fff;
  position: relative;
  overflow: hidden;
}

/* 배경 텍스처 */
.weekly-highlight::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(
    circle at 1px 1px,
    rgba(255,255,255,0.04) 1px,
    transparent 0
  );
  background-size: 20px 20px;
}

.weekly-highlight-label {
  font-family: var(--mono);
  font-size: var(--text-xs);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.55);
  margin-bottom: var(--sp-2);
}

.weekly-highlight-title {
  font-family: var(--serif);
  font-size: var(--text-xl);
  font-weight: 700;
  line-height: 1.38;
  margin-bottom: var(--sp-3);
  position: relative;
}

.weekly-stats {
  display: flex;
  gap: var(--sp-5);
  position: relative;
}

.weekly-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.weekly-stat-num {
  font-family: var(--mono);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.weekly-stat-label {
  font-size: var(--text-xs);
  color: rgba(255,255,255,0.55);
}
```

---

## 5. 상세 페이지 리디자인

### 5-1. 현재 모달/바텀시트 → 슬라이드인 패널

**데스크톱**: 오버레이 모달 → **오른쪽 슬라이드인 패널 (400px)**
- 메인 콘텐츠는 어둡게 처리되지 않음 → 컨텍스트 유지
- 패널이 main 영역 내에서 등장

**모바일**: 바텀시트 → **풀스크린 슬라이드업 (상단 16px 여백)**
- 현재와 유사하지만 전환 효과 개선

```css
/* ===== 상세 패널 v2 ===== */

/* 데스크톱: 오른쪽 슬라이드인 */
@media (min-width: 769px) {
  .detail-v2 {
    position: fixed;
    top: 56px;
    right: 0;
    width: 420px;
    max-width: 42vw;
    height: calc(100vh - 56px);
    background: var(--surface);
    border-left: 1px solid var(--border);
    box-shadow: var(--shadow-4);
    z-index: 21;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    transition: transform var(--t-slow);
    overscroll-behavior: contain;
  }

  .detail-v2.open {
    transform: translateX(0);
  }

  /* 메인 콘텐츠를 왼쪽으로 밀기 (선택적) */
  .main.detail-open {
    margin-right: 420px;
    transition: margin-right var(--t-slow);
  }

  /* 오버레이 없음 — 대신 희미한 tint만 */
  .detail-backdrop {
    display: none; /* 데스크톱에서 사용 안 함 */
  }
}

/* 모바일: 풀스크린 업 */
@media (max-width: 768px) {
  .detail-v2 {
    position: fixed;
    top: 16px; /* 상단 여백 16px → 배경이 살짝 보임 */
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--surface);
    border-radius: var(--r-xl) var(--r-xl) 0 0;
    box-shadow: var(--shadow-modal);
    z-index: 21;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    transform: translateY(100%);
    transition: transform var(--t-slow);
    overscroll-behavior: contain;
  }

  .detail-v2.open {
    transform: translateY(0);
  }

  .detail-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.45);
    z-index: 20;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--t-slow);
  }

  .detail-backdrop.open {
    opacity: 1;
    pointer-events: auto;
  }
}

/* 드래그 핸들 (모바일) */
.detail-handle {
  display: none;
  width: 36px;
  height: 4px;
  background: var(--border2);
  border-radius: 2px;
  margin: 10px auto 0;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .detail-handle { display: block; }
}

/* 상세 헤더 */
.detail-hdr-v2 {
  position: sticky;
  top: 0;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: var(--sp-3) var(--sp-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 1;
  flex-shrink: 0;
}

.detail-hdr-source {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.detail-hdr-breadcrumb {
  font-family: var(--mono);
  font-size: var(--text-xs);
  color: var(--muted);
}

.detail-close-v2 {
  width: 36px;
  height: 36px;
  border-radius: var(--r-sm);
  background: var(--bg2);
  border: 1px solid var(--border);
  cursor: pointer;
  color: var(--text2);
  display: grid;
  place-items: center;
  transition: background var(--t-fast), color var(--t-fast);
}

.detail-close-v2:hover {
  background: var(--bg3);
  color: var(--text);
}

/* 상세 본문 */
.detail-body-v2 {
  padding: var(--sp-5);
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  padding-bottom: calc(var(--mob-nav) + var(--mob-safe) + var(--sp-6));
}

/* 상세 AI 요약 블록 */
.detail-ai-summary {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: var(--sp-5);
  position: relative;
}

.detail-ai-label {
  font-family: var(--mono);
  font-size: var(--text-2xs);
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-3);
}

.detail-ai-label::before {
  content: '';
  width: 16px;
  height: 1.5px;
  background: var(--accent);
}

.detail-ai-text {
  font-size: var(--text-base);
  line-height: 1.8;
  color: var(--text2);
}

/* 키워드 섹션 */
.detail-kws-v2 {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.kw-v2 {
  font-family: var(--mono);
  font-size: var(--text-xs);
  color: var(--accent);
  background: var(--accent-l);
  border: 1px solid var(--accent-m);
  padding: 4px 10px;
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: background var(--t-fast);
}

.kw-v2:hover {
  background: var(--accent-m);
}

/* 액션 버튼 */
.detail-actions-v2 {
  display: flex;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.d-btn-v2 {
  flex: 1;
  min-width: 100px;
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--r-md);
  font-family: var(--sans);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  text-align: center;
  text-decoration: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  transition: all var(--t-base);
}

.d-btn-v2.primary {
  background: var(--accent);
  color: #fff;
  border: none;
}

.d-btn-v2.primary:hover { background: var(--accent-h); }

.d-btn-v2.secondary {
  background: var(--bg);
  color: var(--text2);
  border: 1px solid var(--border);
}

.d-btn-v2.secondary:hover {
  background: var(--bg2);
  border-color: var(--border2);
}

/* 관련 보도자료 */
.detail-related {
  border-top: 1px solid var(--border);
  padding-top: var(--sp-4);
}

.detail-related-title {
  font-family: var(--mono);
  font-size: var(--text-2xs);
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: var(--sp-3);
}

.related-item {
  display: flex;
  gap: var(--sp-3);
  padding: var(--sp-3) 0;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background var(--t-fast);
}

.related-item:last-child { border-bottom: none; }

.related-item-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.related-item-text {
  font-size: var(--text-sm);
  line-height: 1.5;
  color: var(--text2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
```

---

## 6. 인터랙션 & 애니메이션

### 6-1. 페이지 전환 (날짜 변경)

```javascript
async function changeDate(dir) {
  const content = document.getElementById('main-content');
  const wrap = document.getElementById('main-content-wrap');

  // 나가는 방향 애니메이션
  const exitDir = dir > 0 ? 'slide-left' : 'slide-right';
  content.classList.add(exitDir);

  await new Promise(r => setTimeout(r, 120));

  curDate.setDate(curDate.getDate() + dir);
  content.classList.remove(exitDir);
  content.classList.add('invisible');

  await loadData();

  content.classList.remove('invisible');
  const enterDir = dir > 0 ? 'enter-right' : 'enter-left';
  content.classList.add(enterDir);

  requestAnimationFrame(() => {
    content.classList.remove(enterDir);
  });
}
```

```css
@keyframes slideOutLeft {
  to { transform: translateX(-24px); opacity: 0; }
}
@keyframes slideOutRight {
  to { transform: translateX(24px); opacity: 0; }
}
@keyframes slideInFromRight {
  from { transform: translateX(24px); opacity: 0; }
}
@keyframes slideInFromLeft {
  from { transform: translateX(-24px); opacity: 0; }
}

#main-content.slide-left  { animation: slideOutLeft  0.12s ease both; }
#main-content.slide-right { animation: slideOutRight 0.12s ease both; }
#main-content.enter-right { animation: slideInFromRight 0.18s ease both; }
#main-content.enter-left  { animation: slideInFromLeft  0.18s ease both; }
#main-content.invisible   { opacity: 0; }
```

### 6-2. 스켈레톤 로딩 v2

```javascript
function renderSkeleton() {
  const skels = Array(6).fill(0).map((_, i) => `
    <div class="press-card" style="animation:none;cursor:default;pointer-events:none">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <div class="skeleton" style="height:20px;width:${48+i%3*16}px"></div>
        <div class="skeleton" style="height:14px;width:50px"></div>
      </div>
      <div class="skeleton" style="height:16px;width:90%;margin-bottom:8px"></div>
      <div class="skeleton" style="height:16px;width:${65+i%2*15}%;margin-bottom:10px"></div>
      <div class="skeleton" style="height:12px;width:80%;margin-bottom:6px"></div>
      <div class="skeleton" style="height:12px;width:${55+i%3*10}%"></div>
    </div>
  `).join('');

  return `<div class="cards-grid">${skels}</div>`;
}
```

### 6-3. 북마크/공유 마이크로 인터랙션

```javascript
// 북마크 토글
function toggleBookmark(id, btn) {
  const bookmarks = JSON.parse(localStorage.getItem('bookmarks') || '[]');
  const isMarked = bookmarks.includes(id);

  if (isMarked) {
    localStorage.setItem('bookmarks', JSON.stringify(bookmarks.filter(b => b !== id)));
    btn.classList.remove('marked');
  } else {
    bookmarks.push(id);
    localStorage.setItem('bookmarks', JSON.stringify(bookmarks));
    btn.classList.add('marked');

    // 팝 애니메이션
    btn.classList.add('pop');
    setTimeout(() => btn.classList.remove('pop'), 400);
  }
}

// 복사 성공 피드백
async function copyLink() {
  const btn = document.getElementById('copy-btn');
  try {
    await navigator.clipboard.writeText(_shareUrl);
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="ph ph-check"></i> 복사됨';
    btn.style.color = 'var(--success)';
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.style.color = '';
    }, 2000);
  } catch(e) {
    // fallback
  }
}
```

```css
/* 북마크 팝 애니메이션 */
@keyframes bookmarkPop {
  0%   { transform: scale(1); }
  40%  { transform: scale(1.3); }
  70%  { transform: scale(0.9); }
  100% { transform: scale(1); }
}

.bookmark-btn.pop {
  animation: bookmarkPop 0.4s var(--t-spring);
}

.bookmark-btn.marked {
  color: var(--accent);
}

/* 복사 버튼 성공 상태 */
.copy-btn-success {
  color: var(--success) !important;
  border-color: var(--success) !important;
}
```

### 6-4. 카드 입장 애니메이션 (Stagger)

```css
/* 카테고리별로 stagger delay 적용 */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.press-card {
  animation: fadeUp 0.20s ease both;
}

/* 카드 인덱스 기반 딜레이 (JS에서 style.animationDelay 설정) */
/* Math.min(idx, 8) * 0.035 + 's' */
/* 최대 8번째 이후는 동일하게 0.28s */
```

---

## 7. 구현 전략 & 마이그레이션 계획

### 7-1. Vanilla JS 유지 범위

현재 스택(Vanilla JS + 인라인 CSS + 정적 JSON)은 유지합니다.
GitHub Pages 제약, 빌드 툴 없음, 단일 파일 배포가 핵심 제약입니다.

**허용 추가:**
- Phosphor Icons CDN (6KB gzip) — 현재 이모지 대체
- CSS 커스텀 프로퍼티 — 이미 사용 중, 확장만
- Web Animations API — 브라우저 내장, 라이브러리 불필요

**불필요한 것 (추가 안 함):**
- React/Vue 등 프레임워크
- CSS-in-JS
- 번들러
- 애니메이션 라이브러리 (GSAP 등)

### 7-2. CSS 다크모드

```css
/* prefers-color-scheme 기반 자동 + 수동 토글 지원 */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:        #111110;
    --bg2:       #1A1917;
    --bg3:       #232220;
    --surface:   #1C1B19;
    --surface2:  #242320;

    --text:      #EEECEA;
    --text2:     #C4C1BB;
    --text3:     #8A8680;
    --muted:     #5C5955;

    --border:    #2A2926;
    --border2:   #3A3835;
    --border3:   #4A4845;

    --accent:    #4F74E8;
    --accent-h:  #6B8AEE;
    --accent-l:  rgba(79, 116, 232, 0.12);
    --accent-m:  rgba(79, 116, 232, 0.20);
  }
}

[data-theme="dark"] {
  /* 위와 동일한 값 반복 (수동 다크모드) */
}
```

```javascript
// 다크모드 토글 버튼
function toggleDarkMode() {
  const root = document.documentElement;
  const current = root.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}

// 초기화
(function() {
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
})();
```

### 7-3. 성능 최적화

**인라인 CSS 유지하되 구조화:**
```html
<style>
  /* 1. CSS 변수 (토큰) */
  /* 2. 리셋 */
  /* 3. 레이아웃 (header, sidebar, main) */
  /* 4. 컴포넌트 (card, detail, modal) */
  /* 5. 모바일 (미디어 쿼리) */
  /* 6. 패치/오버라이드 */
</style>
```

**폰트 최적화:**
```html
<!-- preload로 FOUT 방지 -->
<link rel="preload" href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap" as="style">
<link rel="preload" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@700&display=swap" as="style">

<!-- font-display: swap 강제 -->
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&family=Noto+Serif+KR:wght@700&family=DM+Mono&display=swap" rel="stylesheet">
```

**가상 스크롤 (100건 이상 시):**
```javascript
// Intersection Observer 기반 lazy 렌더링
const cardObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      cardObserver.unobserve(entry.target);
    }
  });
}, { rootMargin: '100px' });

// 카드 생성 시 observe
document.querySelectorAll('.press-card').forEach(c => cardObserver.observe(c));
```

### 7-4. 단계별 마이그레이션 계획

| 단계 | 내용 | 예상 작업량 | 우선순위 |
|------|------|------------|---------|
| Phase 1 | CSS 변수 → 디자인 시스템 v2 토큰으로 교체 | 2-3시간 | P0 |
| Phase 2 | 이모지 → Phosphor Icons 교체 | 1-2시간 | P0 |
| Phase 3 | 카드 컴포넌트 v2 (버튼 제거, 타이포 위계) | 2시간 | P0 |
| Phase 4 | 사이드바 v2 (날짜/필터/부처 섹션 명확화) | 1시간 | P1 |
| Phase 5 | Topbar v2 (검색 UX 개선, 키보드 단축키) | 1시간 | P1 |
| Phase 6 | 모바일 탭 칩 스타일 + 스크롤 숨김 | 2시간 | P1 |
| Phase 7 | 상세 패널 v2 (슬라이드인, 개선된 레이아웃) | 3시간 | P2 |
| Phase 8 | "오늘의 핵심" 히어로 영역 | 2시간 | P2 |
| Phase 9 | 날짜 전환 슬라이드 애니메이션 | 1시간 | P2 |
| Phase 10 | 다크모드 토글 + CSS 변수 | 2시간 | P3 |
| Phase 11 | 키워드 차트, 카테고리 오버뷰 | 3시간 | P3 |
| Phase 12 | 스와이프 제스처 (상세 닫기, 날짜 변경) | 2시간 | P3 |

**Phase 1-3은 즉시 적용 가능하며 가장 체감 효과가 큽니다.**

### 7-5. Phase 1 즉시 적용 CSS diff 요약

현재 index.html의 `:root` 블록을 위 "디자인 시스템 v2" 섹션의 CSS로 교체하고,
`UI 개선 패치 v2` 섹션은 제거하면 됩니다 (새 변수에 이미 통합).

핵심 변경 포인트:
- `--accent: #2f54eb` → `--accent: #1A47CC` (더 깊은 블루)
- 모든 카테고리 색상 → 채도 절제 버전
- `--shadow-*` 토큰 추가 → 카드/모달에 계층감
- `--r-*` 반경 토큰 추가 → border-radius 일관성
- `--t-*` 트랜지션 토큰 추가 → 애니메이션 일관성
