with open('briefing.py', encoding='utf-8') as f:
    content = f.read()

old = '''    all_items = []
    for crawl_date in crawl_targets:
        if is_weekly:
            print(f"\\n{'='*40}  {crawl_date}  {'='*40}")
        for name, crawler in CRAWLERS:
            for attempt in range(2):
                try:
                    items = crawler(crawl_date)
                    print(f"  -> {name}: {len(items)}건")
                    all_items.extend(items)
                    break
                except Exception as e:
                    if attempt == 0 and "CONNECTION_RESET" in str(e):
                        print(f"  [{name}] Connection Reset -> 10초 후 재시도")
                        time.sleep(random.randint(20, 40))
                    else:
                        print(f"  [{name}] 오류: {e}")
                        break
            time.sleep(random.randint(30, 90))'''

new = '''    all_items = []
    MAX_RETRY = 3  # 최대 재시도 횟수

    for crawl_date in crawl_targets:
        if is_weekly:
            print(f"\\n{'='*40}  {crawl_date}  {'='*40}")

        failed = []  # 실패한 부처 목록

        # 1차 수집
        for name, crawler in CRAWLERS:
            try:
                items = crawler(crawl_date)
                print(f"  -> {name}: {len(items)}건")
                all_items.extend(items)
            except Exception as e:
                print(f"  [{name}] 실패: {str(e)[:80]}")
                failed.append((name, crawler))
            time.sleep(random.randint(30, 90))

        # 재시도 (최대 MAX_RETRY회)
        retry_count = 0
        while failed and retry_count < MAX_RETRY:
            retry_count += 1
            wait_min = 30
            print(f"\\n{'='*60}")
            print(f"  실패 부처 {len(failed)}개 → {wait_min}분 후 재시도 ({retry_count}/{MAX_RETRY})")
            print(f"  재시도 대상: {', '.join(n for n,_ in failed)}")
            print(f"{'='*60}")
            time.sleep(wait_min * 60)

            still_failed = []
            for name, crawler in failed:
                try:
                    items = crawler(crawl_date)
                    print(f"  -> [{name}] 재시도 성공: {len(items)}건")
                    all_items.extend(items)
                except Exception as e:
                    print(f"  [{name}] 재시도 실패: {str(e)[:80]}")
                    still_failed.append((name, crawler))
                time.sleep(random.randint(30, 90))
            failed = still_failed

        if failed:
            print(f"\\n  최종 실패: {', '.join(n for n,_ in failed)}")
        else:
            print(f"\\n  모든 부처 수집 완료!")'''

if old in content:
    content = content.replace(old, new, 1)
    print('완료')
else:
    print('패턴 미발견')
    # 현재 패턴 확인
    idx = content.find('all_items = []')
    print(repr(content[idx:idx+200]))

with open('briefing.py', 'w', encoding='utf-8') as f:
    f.write(content)
