with open('briefing.py', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'target' in line and 'date' in line.lower() and i > 1940:
            print(f'{i}: {line.rstrip()}')
