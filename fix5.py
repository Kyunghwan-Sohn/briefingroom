with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

# wp_post 위치
wp_post_pos = next(i for i,l in enumerate(lines) if l.startswith('def wp_post('))
# wp_get_or_create_category 위치
wp_get_pos = next(i for i,l in enumerate(lines) if l.startswith('def wp_get_or_create_category'))
# main 위치
main_pos = next(i for i,l in enumerate(lines) if l.startswith('def main():'))

print(f'wp_post: {wp_post_pos}, wp_get: {wp_get_pos}, main: {main_pos}')

# wp_get ~ 파일끝 블록을 wp_post 앞으로 이동
wp_get_block = lines[wp_get_pos:]
new_lines = lines[:wp_post_pos] + wp_get_block + lines[wp_post_pos:wp_get_pos]

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('완료')

# 확인
with open('briefing.py', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if line.startswith('def wp_') or line.startswith('def main'):
            print(f'{i}: {line.rstrip()}')
