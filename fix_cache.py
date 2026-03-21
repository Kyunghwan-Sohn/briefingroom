with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

# _wp_cat_cache = {} 위치 찾기
cache_pos = next(i for i,l in enumerate(lines) if l.strip() == '_wp_cat_cache = {}')
posted_pos = next(i for i,l in enumerate(lines) if '_posted_titles: set = set()' in l)
print(f'_wp_cat_cache: {cache_pos+1}, _posted_titles: {posted_pos+1}')

# _wp_cat_cache 줄 제거 후 _posted_titles 바로 아래에 삽입
cache_line = lines[cache_pos]
new_lines = lines[:cache_pos] + lines[cache_pos+1:]
posted_pos2 = next(i for i,l in enumerate(new_lines) if '_posted_titles: set = set()' in l)
new_lines.insert(posted_pos2 + 1, cache_line)

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('완료')

# 확인
with open('briefing.py', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if '_wp_cat_cache' in line or '_posted_titles' in line.strip()[:20]:
            print(f'{i}: {line.rstrip()}')
