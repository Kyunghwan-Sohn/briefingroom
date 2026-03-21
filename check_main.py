with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

main_start = next(i for i,l in enumerate(lines) if l.strip() == 'def main():')
print(f'main 시작: {main_start+1}')
# main 끝 찾기 (다음 def 또는 if __name__)
main_end = main_start + 1
while main_end < len(lines):
    if lines[main_end].startswith('def ') or lines[main_end].startswith('if __name__'):
        break
    main_end += 1
print(f'main 끝: {main_end+1}')
print(''.join(lines[main_start:main_start+30]))
