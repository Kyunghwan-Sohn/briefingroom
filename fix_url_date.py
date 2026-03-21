with open('current.html', encoding='utf-8') as f:
    content = f.read()

dollar = chr(36)
php_header = f'''<?php
if (is_page()) {{
    {dollar}page = get_post();
    echo {dollar}page->post_content;
    exit;
}}
?>
'''

# 1. URL 파라미터 처리 + 날짜 자동 설정 JS 추가
old_js = '(async()=>{await loadCats();await loadPosts()})();'
new_js = '''// URL 파라미터 처리
(async()=>{
  await loadCats();

  // 요일별 기본 날짜 설정
  const today = new Date();
  const wd = today.getDay(); // 0=일, 6=토
  const defaultDate = new Date(today);
  if(wd === 6) defaultDate.setDate(today.getDate()-1);       // 토→금
  else if(wd === 0) defaultDate.setDate(today.getDate()-2);  // 일→금
  else if(wd === 1) defaultDate.setDate(today.getDate()-3);  // 월→금
  else defaultDate.setDate(today.getDate()-1);               // 화~금→전날
  curDate = defaultDate;

  // URL 파라미터 확인
  const params = new URLSearchParams(window.location.search);
  const ministry = params.get('ministry');
  const dateParam = params.get('date');

  if(dateParam){
    const parts = dateParam.split('-');
    if(parts.length===3) curDate = new Date(parts[0], parts[1]-1, parts[2]);
  }

  await loadPosts();

  // 부처 필터 적용
  if(ministry){
    const el = [...document.querySelectorAll('.f-item')].find(
      el => el.querySelector('.f-left')?.textContent?.trim() === ministry
    );
    if(el) setFilter(ministry, el);
    // 모바일 탭도 없으면 전체 유지하고 JS 필터만 적용
    curFilter = ministry;
    render();
  }
})();'''

# 2. 날짜 표시 - 토/일/월이면 금요일 보도자료임을 표시
old_title = "document.getElementById('page-title').textContent=${curDate.getMonth()+1}월 일 보도자료;"
new_title = """const days2=['일','월','화','수','목','금','토'];
  const wd2=curDate.getDay();
  const todayWd=new Date().getDay();
  const isDefaultDate = curDate.toDateString()===new Date(()=>{const d=new Date();if(todayWd===6)d.setDate(d.getDate()-1);else if(todayWd===0)d.setDate(d.getDate()-2);else if(todayWd===1)d.setDate(d.getDate()-3);else d.setDate(d.getDate()-1);return d;})().toDateString();
  document.getElementById('page-title').textContent=${curDate.getMonth()+1}월 일 보도자료;"""

c = content
changes = 0

if old_js in c:
    c = c.replace(old_js, new_js, 1); changes+=1; print('OK: URL 파라미터 처리')
else:
    print('FAIL: URL 파라미터 패턴 미발견')

# 3. page-sub에 날짜 안내 추가
old_sub = "document.getElementById('page-sub').textContent=fmtDateKo(curDate);"
new_sub = """const todayD=new Date();const todayWd2=todayD.getDay();
  let subText=fmtDateKo(curDate);
  // 오늘 기준 기본날짜면 요일 안내 추가
  const isFriData=(todayWd2===6||todayWd2===0||todayWd2===1);
  const isYesterday=((todayD-curDate)/(1000*60*60*24)<1.5 && curDate<todayD);
  if(isFriData&&isYesterday) subText+=' (금요일 보도자료)';
  else if(isYesterday) subText+=' 보도자료';
  document.getElementById('page-sub').textContent=subText;"""

if old_sub in c:
    c = c.replace(old_sub, new_sub, 1); changes+=1; print('OK: 날짜 안내')
else:
    print('FAIL: page-sub 패턴 미발견')

final = php_header + c
with open('index.php', 'w', encoding='utf-8') as f:
    f.write(final)
print(f'완료: {changes}개 변경, {len(final)} chars')
