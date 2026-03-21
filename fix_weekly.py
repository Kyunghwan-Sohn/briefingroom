with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

# 기존 main에서 크롤링 루프 찾기
old = '''    all_items = []
    for name, crawler in CRAWLERS:
        for attempt in range(2):  # 실패 시 1회 재시도
            try:
                items = crawler(target)
                print(f"  → {name}: {len(items)}건")
                all_items.extend(items)
                break
            except Exception as e:
                if attempt == 0 and "CONNECTION_RESET" in str(e):
                    print(f"  [{name}] Connection Reset → 10초 후 재시도")
                    time.sleep(10)
                else:
                    print(f"  [{name}] 오류: {e}")
                    break
        time.sleep(30)  # 부처 간 딜레이 30초 (IP 차단 방지)'''

new = '''    all_items = []
    crawl_targets = target_dates if is_weekly else [target]

    for crawl_date in crawl_targets:
        if is_weekly:
            print(f"\\n{'='*40}")
            print(f"  수집 날짜: {crawl_date}")
            print(f"{'='*40}")
        for name, crawler in CRAWLERS:
            for attempt in range(2):
                try:
                    items = crawler(crawl_date)
                    print(f"  → {name}: {len(items)}건")
                    all_items.extend(items)
                    break
                except Exception as e:
                    if attempt == 0 and "CONNECTION_RESET" in str(e):
                        print(f"  [{name}] Connection Reset → 10초 후 재시도")
                        time.sleep(10)
                    else:
                        print(f"  [{name}] 오류: {e}")
                        break
            time.sleep(30)'''

if old in content:
    content = content.replace(old, new, 1)
    print('크롤링 루프 수정 완료')
else:
    print('패턴 미발견')

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
