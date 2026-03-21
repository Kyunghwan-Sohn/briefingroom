with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

main_start = next(i for i,l in enumerate(lines) if l.strip() == 'def main():')
print(f'main 시작: {main_start+1}')
print(''.join(lines[main_start:main_start+25]))
