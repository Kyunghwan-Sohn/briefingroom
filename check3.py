with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

# 모든 def 위치 찾기
for i, line in enumerate(lines, 1):
    if line.startswith('def ') or line.startswith('CAT_MAP') or line.startswith('_posted'):
        print(f'{i}: {line.rstrip()}')
