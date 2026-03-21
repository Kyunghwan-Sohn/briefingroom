content = open('briefing.py', encoding='utf-8').read()
old = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
new = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
count = content.count(old)
print(f'패턴 {count}개 발견')
content = content.replace(old, new)
old2 = 'args=["--disable-blink-features=AutomationControlled"]'
new2 = 'args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]'
count2 = content.count(old2)
print(f'args 패턴 {count2}개 발견')
content = content.replace(old2, new2)
open('briefing.py', 'w', encoding='utf-8').write(content)
print('완료')
