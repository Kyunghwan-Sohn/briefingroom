with open('index.php', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines[:15], 1):
    print(f'{i}: {repr(l)}')
