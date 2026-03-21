with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

# extract_hwp 호출 부분 찾기
idx = content.find('extract_hwp(')
print(repr(content[idx-100:idx+200]))
