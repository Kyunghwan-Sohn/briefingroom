with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

# 2150, 2151줄 삭제 (0-indexed: 2149, 2150)
del lines[2149:2152]

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('완료')
