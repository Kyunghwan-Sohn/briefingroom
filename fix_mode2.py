with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

main_start = next(i for i,l in enumerate(lines) if l.strip() == 'def main():')

# 교체할 블록 끝 찾기 (is_weekly = False 다음 target_dates = [target] 줄)
end = main_start + 1
while end < len(lines):
    if '            is_weekly = False' in lines[end] and 'sys.argv' not in lines[end]:
        end += 2  # target_dates = [target] 줄까지
        break
    end += 1

print(f'교체 범위: {main_start+1}~{end+1}줄')

new_block = '''def main():
    import os
    from datetime import timedelta
    today = date.today()
    weekday = today.weekday()  # 0=월 4=금 5=토 6=일

    run_mode = os.environ.get('RUN_MODE', 'auto')
    run_date = os.environ.get('RUN_DATE', '')

    if run_mode == 'weekly':
        is_weekly = True
    elif run_mode == 'daily':
        is_weekly = False
    else:
        # auto: 토(5)/일(6) → 주간, 나머지 → 일별
        is_weekly = weekday in (5, 6)

    if is_weekly:
        # 가장 최근 금요일 기준 월~금
        last_friday = today
        while last_friday.weekday() != 4:
            last_friday -= timedelta(days=1)
        last_monday = last_friday - timedelta(days=4)
        target_dates = [last_monday + timedelta(days=i) for i in range(5)]
        target = last_friday
    else:
        # 일별: 당일
        target = today
        if run_date:
            try:
                target = date.fromisoformat(run_date)
            except ValueError:
                pass
        target_dates = [target]

'''

new_lines = lines[:main_start] + [new_block] + lines[end:]
with open('briefing.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('완료')

with open('briefing.py', encoding='utf-8') as f:
    content = f.read()
idx = content.find('def main():')
print(content[idx:idx+500])
