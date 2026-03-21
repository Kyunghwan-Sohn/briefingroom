with open('briefing.py', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if '_wp_cat_cache' in line or '_posted_titles' in line or 'CAT_MAP' in line.strip()[:10]:
            print(f'{i}: {line.rstrip()}')
