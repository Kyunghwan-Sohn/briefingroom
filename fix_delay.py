with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

import random

# 부처간 딜레이 30초 고정 → 30~90초 랜덤으로 변경
old = '            time.sleep(30)'
new = '            time.sleep(random.randint(30, 90))'

# Connection Reset 재시도 딜레이 10초 → 20~40초 랜덤
old2 = '                        time.sleep(10)'
new2 = '                        time.sleep(random.randint(20, 40))'

# random import 확인 후 추가
if 'import random' not in content:
    content = 'import random\n' + content
    print('random import 추가')

c = content
changes = 0
for old, new in [(old, new), (old2, new2)]:
    if old in c:
        c = c.replace(old, new); changes+=1; print('OK: ' + old.strip())
    else:
        print('FAIL: ' + old.strip())

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(c)
print(f'완료: {changes}개 변경')
