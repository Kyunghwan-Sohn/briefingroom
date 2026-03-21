with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

# main 함수 내 all_items = [] 부터 크롤링 루프 끝까지 찾아서 교체
start = next(i for i,l in enumerate(lines) if '    all_items = []' in l)
# time.sleep(random.randint(30, 90)) 이후 빈줄 찾기
end = start + 1
while end < len(lines):
    if '    time.sleep(random.randint(30, 90))' in lines[end]:
        end += 1
        break
    end += 1

print(f'교체 범위: {start+1}~{end+1}줄')
print(''.join(lines[start:end]))
