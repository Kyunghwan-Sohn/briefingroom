content = open('briefing.py', encoding='utf-8').read()
old = 'target = date.today()'
new = 'target = date(2026, 3, 20)  # 테스트용'
if old in content:
    content = content.replace(old, new, 1)
    open('briefing.py', 'w', encoding='utf-8').write(content)
    print('완료')
else:
    print('패턴 미발견')
    idx = content.find('target')
    print(repr(content[idx:idx+100]))
