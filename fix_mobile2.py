with open('current.html', encoding='utf-8') as f:
    content = f.read()

php_header = '<?php\nif (is_page()) {\n    ' + chr(36) + 'page = get_post();\n    echo ' + chr(36) + 'page->post_content;\n    exit;\n}\n?>\n'

# 1. 모바일 CSS 추가
old_css = '@media(max-width:768px){'
new_css = '''/* 모바일 특화 */
.mob-date-nav{display:none;align-items:center;justify-content:space-between;background:var(--surface);border-bottom:1px solid var(--border);padding:8px 16px;position:sticky;top:56px;z-index:7}
.mob-date-info{text-align:center}
.mob-date-main{font-family:var(--serif);font-size:15px;font-weight:700;color:var(--text)}
.mob-date-sub{font-family:var(--mono);font-size:10px;color:var(--accent);margin-top:2px}
.mob-arr{background:var(--bg2);border:1px solid var(--border);border-radius:7px;padding:6px 14px;font-size:13px;color:var(--text);cursor:pointer;border:none}
.mob-cat-tabs{display:none;gap:6px;padding:8px 16px;overflow-x:auto;background:var(--surface);border-bottom:1px solid var(--border);-webkit-overflow-scrolling:touch}
.mob-cat-tab{padding:5px 12px;border-radius:20px;font-size:11px;font-weight:500;white-space:nowrap;cursor:pointer;border:1px solid var(--border);color:var(--text2);background:var(--bg2);flex-shrink:0}
.mob-cat-tab.active{background:var(--accent);color:#fff;border-color:var(--accent)}
@media(max-width:768px){
  .mob-date-nav{display:flex}
  .mob-cat-tabs{display:flex}
  .sidebar{display:none}
  .main{margin-left:0}
  .cards-grid{grid-template-columns:1fr}
  .detail{width:100%;right:-100%}
  .popup{max-height:80vh;overflow-y:auto;border-radius:14px 14px 0 0;position:fixed;bottom:0;left:0;right:0;width:100%;max-width:100%}
  .overlay{align-items:flex-end;padding:0}
  .min-grid{grid-template-columns:repeat(3,1fr)}
  .sub-bar-sel{display:none}
  .topbar{top:0}'''

# 2. 모바일 날짜 네비 + 카테고리 탭 HTML 추가
old_html = '    <div class="topbar">'
new_html = '''    <div class="mob-date-nav" id="mob-date-nav">
      <button class="mob-arr" onclick="changeDate(-1)">&#9664; 이전</button>
      <div class="mob-date-info">
        <div class="mob-date-main" id="mob-date-main"></div>
        <div class="mob-date-sub" id="mob-date-sub"></div>
      </div>
      <button class="mob-arr" onclick="changeDate(1)">다음 &#9654;</button>
    </div>
    <div class="mob-cat-tabs" id="mob-cat-tabs">
      <div class="mob-cat-tab active" onclick="mobSetFilter('all',this)">전체</div>
      <div class="mob-cat-tab" onclick="mobSetFilter('금융경제',this)">금융·경제</div>
      <div class="mob-cat-tab" onclick="mobSetFilter('사회복지',this)">사회·복지</div>
      <div class="mob-cat-tab" onclick="mobSetFilter('산업기술',this)">산업·기술</div>
      <div class="mob-cat-tab" onclick="mobSetFilter('외교안보',this)">외교·안보</div>
      <div class="mob-cat-tab" onclick="mobSetFilter('행정법제',this)">행정·법제</div>
    </div>
    <div class="topbar">'''

# 3. JS - 날짜 네비 업데이트 + 모바일 필터 함수 추가
old_js = "document.getElementById('date-label').textContent=ds;"
new_js = """document.getElementById('date-label').textContent=ds;
  // 모바일 날짜 표시
  const days=['일','월','화','수','목','금','토'];
  const mobMain=document.getElementById('mob-date-main');
  const mobSub=document.getElementById('mob-date-sub');
  if(mobMain) mobMain.textContent=curDate.getMonth()+1+'월 '+curDate.getDate()+'일 '+days[curDate.getDay()]+'요일';
  if(mobSub){
    const wd=curDate.getDay();
    // 토요일(6), 일요일(0), 월요일(1) → 금요일 보도자료 안내
    const prevDay=new Date(curDate);prevDay.setDate(prevDay.getDate()-1);
    const isToday=ds===new Date().toISOString().slice(0,10);
    if(isToday&&(wd===6||wd===0||wd===1)){
      const fri=new Date(curDate);
      if(wd===6)fri.setDate(fri.getDate()-1);
      else if(wd===0)fri.setDate(fri.getDate()-2);
      else fri.setDate(fri.getDate()-3);
      mobSub.textContent='금요일('+( fri.getMonth()+1)+'/'+fri.getDate()+') 보도자료';
    } else {
      mobSub.textContent=prevDay.getMonth()+1+'월 '+prevDay.getDate()+'일 보도자료';
    }
  }"""

# 4. 모바일 필터 JS 함수 추가
old_script_end = '(async()=>{await loadCats();await loadPosts()})();'
new_script_end = '''(async()=>{await loadCats();await loadPosts()})();

function mobSetFilter(cat,el){
  document.querySelectorAll('.mob-cat-tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  // 사이드바 필터도 동기화
  document.querySelectorAll('.f-item').forEach(i=>i.classList.remove('active'));
  curFilter=cat;expanded={};render();
}'''

c = content
changes = 0
for old, new in [(old_css,new_css),(old_html,new_html),(old_js,new_js),(old_script_end,new_script_end)]:
    if old in c:
        c = c.replace(old, new, 1); changes+=1; print('OK: '+old[:35])
    else:
        print('FAIL: '+old[:35])

final = php_header + c
with open('index.php', 'w', encoding='utf-8') as f:
    f.write(final)
print(f'완료: {changes}개 변경, {len(final)} chars')
