with open('current.html', encoding='utf-8') as f:
    content = f.read()

php_header = '''<?php
if (is_page()) {
     = get_post();
    echo ->post_content;
    exit;
}
?>
'''

old_css = '@media(max-width:768px){'
new_css = '''.mobile-date-nav{display:none;align-items:center;justify-content:space-between;background:var(--surface);border-bottom:1px solid var(--border);padding:10px 16px;position:sticky;top:56px;z-index:7}
.mob-date-label{font-family:var(--mono);font-size:13px;color:var(--text2);font-weight:500}
.mob-date-arrow{background:var(--bg2);border:1px solid var(--border);border-radius:7px;padding:5px 14px;cursor:pointer;color:var(--text);font-size:13px}
@media(max-width:768px){
  .mobile-date-nav{display:flex}'''

old_html = '    <div class="topbar">'
new_html = '''    <div class="mobile-date-nav" id="mobile-date-nav">
      <button class="mob-date-arrow" onclick="changeDate(-1)">&#9664; 이전</button>
      <span class="mob-date-label" id="mobile-date-label"></span>
      <button class="mob-date-arrow" onclick="changeDate(1)">다음 &#9654;</button>
    </div>
    <div class="topbar">'''

old_js = "document.getElementById('date-label').textContent=ds;"
new_js = """document.getElementById('date-label').textContent=ds;
  const mbl=document.getElementById('mobile-date-label');
  if(mbl) mbl.textContent=curDate.getMonth()+1+'월 '+curDate.getDate()+'일';"""

c = content
changes = 0
for old, new in [(old_css,new_css),(old_html,new_html),(old_js,new_js)]:
    if old in c:
        c = c.replace(old, new, 1); changes+=1; print('OK: '+old[:30])
    else:
        print('FAIL: '+old[:30])

final = php_header + c
with open('index.php', 'w', encoding='utf-8') as f:
    f.write(final)
print(f'완료: {changes}개 변경')
