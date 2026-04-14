# govbrief.kr UI/UX 및 콘텐츠 분석 리포트

분석 대상은 [홈](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:59), [오늘 발표](/Users/kyunghwansohn/Desktop/briefingroom_new/brief/today/index.html:33), [키워드 트렌드](/Users/kyunghwansohn/Desktop/briefingroom_new/keywords/index.html:40), [규제 트래커](/Users/kyunghwansohn/Desktop/briefingroom_new/regulation/index.html:38), [정책 AI](/Users/kyunghwansohn/Desktop/briefingroom_new/policy/index.html:19)이다. 정책 AI는 실제 화면 없이 `/brief/`로 리다이렉트돼 IA 결손 신호로 반영했다([policy/index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/policy/index.html:5)).

## 웹(1280px)

### 1. UI 분석
As-Is: 공통 `body`는 `15px/1.6`인데 실제 정보 단위는 검색 `13px`, 시간 `12px`, 홈 `top-title 14px`, 중요도 배지 `10px`, 오늘 발표 메타 `10~12px`까지 내려간다([index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:59), [index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:117), [brief/today/index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/brief/today/index.html:98)). 색상은 `--t/#1a1a1a`, `--t2/#555`, `--t3/#888`, `--m/#bbb`, `--a/#d96c2c`인데 대비는 `#888` 3.54:1, `#bbb` 1.92:1, `#d96c2c` 3.42:1로 AA 미달이다. 레이아웃은 대체로 `max-width:1080px`지만 카드 radius가 6/8/10px로 분산된다.

문제점: 1280px에서도 메타와 필터가 작아 스캔보다 해독에 시간이 걸리고, 회색 보조 텍스트가 실제로는 읽기 어렵다. 카드 문법이 페이지마다 달라 제품 톤도 흔들린다.

To-Be: 웹 기본을 `body 16/1.7`, `panel-title 24`, `body-sm 14`, `caption 12`로 올리고 12px 미만 텍스트를 금지한다. `--t3`는 `#6b7280`, `--m`은 `#9ca3af`로 조정하고 카드 토큰은 `radius 10`, `padding 20~24`로 통합한다.

우선순위: P0 타이포 스케일 상향, P0 대비 보정, P1 카드/반경 토큰 통합.

### 2. UX 분석
As-Is: 홈은 “오늘 발표 → 키워드 → 규제” 3패널 구조이고([index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:292)), 헤더 검색은 홈/키워드/규제 모두 입력창만 존재하고 동작이 없다([index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:284), [keywords/index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/keywords/index.html:362), [regulation/index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/regulation/index.html:257)). 오늘 발표만 필터가 실제 구현돼 있고([brief/today/index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/brief/today/index.html:997)), 정책 AI는 별도 메뉴 없이 리다이렉트된다.

문제점: 사용자의 1순위는 “오늘 영향 있는 변화”인데 홈은 세 섹션이 동급으로 보여 우선순위가 약하다. 검색은 기대만 만들고, 정책 AI 심화 동선도 약하다.

To-Be: 홈 첫 패널을 “영향도 높은 발표 + 규제 변화” 혼합형으로 바꾸고, 2번째에 규제, 3번째에 키워드를 둔다. 비동작 검색은 숨기거나 준비중으로 표시하고, 정책 AI는 헤더 또는 규제 패널 상단 CTA로 승격한다.

우선순위: P0 검색 기대관리, P1 홈 정보 우선순위 재배치, P1 정책 AI 진입 동선 복구.

### 3. 고객 여정 분석
As-Is: 핵심 페르소나는 기업 실무자, 정책 담당자, 금융·부동산 전문가다. 여정은 홈 진입 → 요약 스캔 → 상세 진입 구조이며, 강한 CTA는 규제 페이지 `FinLaw GPT` 정도다([regulation/index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/regulation/index.html:280)).

문제점: 진입 단계의 긴급성, 심화 단계의 근거, 재방문 단계의 알림 가치가 모두 약하다.

To-Be: 여정을 `즉시 영향 확인 → 분야 필터 → 원문/근거 확인 → 알림 구독·AI 질문`으로 재정의한다. 홈/오늘 발표에 “영향도 상”, “관련 규제”, “원문”, “AI 질문” CTA를 추가하고, 재방문은 “매일 변경 브리핑 받기”로 단순화한다.

우선순위: P0 신뢰/근거 CTA, P1 개인화·알림 CTA, P2 저장/구독 여정 고도화.

### 4. 콘텐츠 구성 분석
As-Is: 홈 3개 패널은 pill, treemap, 2x2 카드로 모두 다른 시각 언어를 사용한다([index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:301), [index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:368), [index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:447)). 첫 패널은 키워드, 범례, 리스트가 겹쳐 가장 복잡하다.

문제점: 홈 첫 스캔 비용이 높고, treemap과 언론 반응 바가 행동 유도보다는 주목도 위주다. AI 요약 신뢰 표식도 약하다.

To-Be: 홈 첫 패널을 `영향도 상 3건 + AI 한줄 인사이트 + 관련 규제` 중심으로 단순화한다. treemap은 상세 탐색용으로 내리고, AI 요약에는 “원문 기반”, “생성 시각”, “관련 법령 수” 배지를 붙인다.

우선순위: P1 홈 첫 패널 재편, P1 AI 신뢰 표식 강화, P2 시각화의 역할 분리.

## 모바일웹(390px)

### 1. UI/UX 통합 분석
As-Is: 모바일 기본은 `14px/1.55`지만 실제 네비 `12px`, 바텀네비 `10.5px`, 규제 카드 본문 `11px`, 오늘 발표 선택값 `10px`까지 내려간다([index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/index.html:193), [brief/today/index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/brief/today/index.html:75)). 홈 규제 카드는 2열이고, 키워드 hero 서브카피는 숨겨진다([keywords/index.html](/Users/kyunghwansohn/Desktop/briefingroom_new/keywords/index.html:236)).

문제점: 390px에서 “작은 글자 + 2열 카드 + 하단 고정 네비” 조합으로 가독성이 급락한다. CTA도 약해 첫 행동이 불분명하다.

To-Be: 모바일 최소 텍스트를 `body 15`, `meta 12`, `nav 11.5`, `caption 11`로 올리고 10px 사용을 제거한다. 홈 규제 카드는 1열, 키워드 서브카피는 2줄 복구, AI CTA는 설명 2줄과 넓은 버튼으로 재구성한다.

우선순위: P0 모바일 폰트 상향, P0 홈 규제 1열화, P1 CTA 가시성 강화.

### 2. 고객 여정/이탈 리스크
As-Is: 모바일은 홈 진입 → 요약 스캔 → 바텀네비 이동 흐름이다. 오늘 발표만 필터가 완성돼 있고, 홈 검색은 비동작이며 정책 AI도 찾기 어렵다.

문제점: 첫 방문자는 “무엇을 눌러야 하는지”가 먼저 보여야 하는데 현재 모바일 홈은 우선 행동이 없다. 검색 미작동과 리다이렉트 페이지도 이탈 요인이다.

To-Be: 모바일 상단에 `오늘 영향 큰 3건`, `내 산업 키워드`, `규제 질문하기` 중 핵심 CTA를 고정 배치한다. 상세 하단에는 `원문`, `관련 규제`, `AI 질문` sticky 액션 바를 둔다.

우선순위: P0 모바일 시작 CTA 신설, P1 상세 액션 바 추가, P2 개인화 저장.
