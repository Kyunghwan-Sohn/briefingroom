with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

# WP 변수 위치 찾기
wp_start = next(i for i,l in enumerate(lines) if l.startswith('WP_URL'))
wp_end = wp_start + 3

# WP 변수 블록 추출
wp_block = lines[wp_start:wp_end]
print('이동할 블록:')
for l in wp_block:
    print(repr(l))

# CAT_MAP 위치 찾기 - 여기 앞에 삽입
cat_pos = next(i for i,l in enumerate(lines) if l.startswith('CAT_MAP = {'))
print(f'CAT_MAP 위치: {cat_pos+1}')

# WP 변수 제거 후 CAT_MAP 앞에 삽입
new_lines = lines[:wp_start] + lines[wp_end:]
cat_pos2 = next(i for i,l in enumerate(new_lines) if l.startswith('CAT_MAP = {'))
new_lines = new_lines[:cat_pos2] + wp_block + ['\n'] + new_lines[cat_pos2:]

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('완료')

# 확인
with open('briefing.py', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if line.startswith('WP_URL') or line.startswith('WP_USER') or line.startswith('WP_PASS') or line.startswith('CAT_MAP'):
            print(f'{i}: {line.rstrip()}')
