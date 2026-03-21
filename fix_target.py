with open('index.php', encoding='utf-8') as f:
    content = f.read()

old = '<a class="d-btn sec" id="d-wp" href="#" target="_blank">\U0001f4c4 \uc0c1\uc138 \uae00</a>'
new = '<a class="d-btn sec" id="d-wp" href="#">\U0001f4c4 \uc0c1\uc138 \uae00</a>'

if old in content:
    content = content.replace(old, new, 1)
    print('target 제거 완료')
else:
    # 직접 찾기
    idx = content.find('d-wp" href="#"')
    print(repr(content[idx:idx+80]))

with open('index.php', 'w', encoding='utf-8') as f:
    f.write(content)
