content = open('briefing.py', encoding='utf-8').read()
lines = content.split('\n')
keywords = ['def wp_post', 'def wp_check', 'def main', '_posted_titles: set', 'CAT_MAP = {']
for i, l in enumerate(lines):
    for k in keywords:
        if k in l:
            print(f'{i+1}: {l.strip()}')
