with open('briefing.py', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'def wp_' in line:
            print(f'{i}: {line.rstrip()}')
