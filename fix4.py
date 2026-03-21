content = open('briefing.py', encoding='utf-8').read()
lines = content.split('\n')

# CAT_MAP 위치 찾기
cat_map_pos = next(i for i,l in enumerate(lines) if l.startswith('CAT_MAP = {'))
wp_check_pos = next(i for i,l in enumerate(lines) if '_posted_titles: set = set()' in l)
print(f'CAT_MAP: {cat_map_pos}, wp_check: {wp_check_pos}')

# CAT_MAP 블록 추출 (다음 빈줄까지)
end = cat_map_pos + 1
while end < len(lines) and (lines[end].startswith(' ') or lines[end].startswith('\t') or lines[end].strip().startswith('"') or lines[end].strip().startswith("'") or lines[end].strip() == '}'):
    end += 1
cat_block = lines[cat_map_pos:end]
print(f'CAT_MAP 블록: {len(cat_block)}줄')

# CAT_MAP 제거 후 wp_check 앞에 삽입
new_lines = lines[:cat_map_pos] + lines[end:]
wp_pos2 = next(i for i,l in enumerate(new_lines) if '_posted_titles: set = set()' in l)
new_lines = new_lines[:wp_pos2] + cat_block + [''] + new_lines[wp_pos2:]
open('briefing.py', 'w', encoding='utf-8').write('\n'.join(new_lines))
print('완료')
