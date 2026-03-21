with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines[2140:2160], 2141):
    print(f'{i}: {repr(l)}')
