with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

# 테스트용 날짜 고정 제거 확인
if 'target = date(2026' in content:
    content = content.replace("target = date(2026, 3, 20)  # 테스트용", "")
    with open('briefing.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('날짜 고정 제거 완료')
else:
    print('날짜 고정 없음 - OK')
