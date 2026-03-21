with open('briefing.py', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if line.startswith('WP_URL') or line.startswith('WP_USER') or line.startswith('WP_PASS'):
            print(f'{i}: {line.rstrip()}')
