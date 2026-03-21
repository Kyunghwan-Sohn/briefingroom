with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

# 기존 target 설정 찾기
old = 'target = date(2026, 3, 20)  # 테스트용'
new = '''# 요일별 수집 날짜 자동 설정
today = date.today()
weekday = today.weekday()  # 0=월, 1=화, ..., 6=일

if weekday in (6, 0):  # 일요일, 월요일 → 주간 모음 모드
    is_weekly = True
    # 지난주 월~금
    days_to_monday = weekday if weekday == 0 else 1
    last_friday = today - timedelta(days=today.weekday() + 3 if weekday == 0 else today.weekday() + 2)
    last_monday = last_friday - timedelta(days=4)
    target_dates = [last_monday + timedelta(days=i) for i in range(5)]
    target = target_dates[-1]  # 대표 날짜는 금요일
else:
    is_weekly = False
    target = today - timedelta(days=1)  # 전날
    target_dates = [target]'''

if old in content:
    content = content.replace(old, new, 1)
    print('target 수정 완료')
else:
    print('패턴 미발견 - 현재 target 설정 확인')
    idx = content.find('target = date')
    if idx == -1:
        idx = content.find('target = ')
    print(repr(content[idx:idx+100]))

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
