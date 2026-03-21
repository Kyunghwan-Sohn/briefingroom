with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

main_start = next(i for i,l in enumerate(lines) if l.strip() == 'def main():')
main_end = main_start + 1
while main_end < len(lines):
    if lines[main_end].startswith('def ') or lines[main_end].startswith('if __name__'):
        break
    main_end += 1

new_main = '''def main():
    from datetime import timedelta
    today = date.today()
    weekday = today.weekday()  # 0=월 6=일

    # 요일별 날짜 설정
    if weekday in (6, 0):  # 일/월 → 주간 모음
        is_weekly = True
        if weekday == 0:  # 월요일
            last_friday = today - timedelta(days=3)
        else:  # 일요일
            last_friday = today - timedelta(days=2)
        last_monday = last_friday - timedelta(days=4)
        target_dates = [last_monday + timedelta(days=i) for i in range(5)]
        target = target_dates[-1]
    else:
        is_weekly = False
        target = today - timedelta(days=1)
        target_dates = [target]

    if len(sys.argv) > 1:
        try:
            target = date.fromisoformat(sys.argv[1])
            target_dates = [target]
            is_weekly = False
        except ValueError:
            print("날짜 형식 오류. 예: python briefing.py 2026-03-18")
            sys.exit(1)

    print(f"{'='*60}")
    if is_weekly:
        print(f"  브리핑룸  |  주간 모음  |  {target_dates[0]} ~ {target_dates[-1]}")
    else:
        print(f"  브리핑룸  |  {target}  |  {len(CRAWLERS)}개 부처")
    print(f"{'='*60}")

    all_items = []
    for crawl_date in target_dates:
        if is_weekly:
            print(f"\\n{'='*40}  {crawl_date}  {'='*40}")
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
            time.sleep(30)

    print(f"\\n{'─'*60}")
    print(f"총 {len(all_items)}건 수집\\n")

    print("[파일 처리 중...]")
    for item in all_items:
        if not (item["pdfs"] or item["hwps"]): continue
        process_item(item)

    print(f"\\n{'─'*60}")
    print("[LLM 요약 중...]")
    for item in all_items:
        item["summary"] = summarize(item)
        print(f"  summary: {item['summary'][:60]}")
        time.sleep(0.5)

    print(f"\\n{'─'*60}")
    print("[WordPress 포스팅 중...]")
    wp_count = 0
    for item in all_items:
        if wp_post(item):
            wp_count += 1
    print(f"  ✅ WordPress 포스팅 완료: {wp_count}건")

    print(f"\\n{'='*60}")
    print(f"  완료  |  {target}  |  총 {len(all_items)}건")
    print(f"{'='*60}")

    print(f"\\n{'─'*60}")
    for name, _ in CRAWLERS:
        cnt = sum(1 for i in all_items if i["source"] == name)
        mark = "✅" if cnt > 0 else "⚪"
        print(f"  {mark} {name:<20} {cnt}건")
    print(f"{'─'*60}")
    print(f"  합계: {len(all_items)}건")
    print(f"  파일: {PDF_DIR}")
    print(f"  텍스트: {TXT_DIR}")

'''

new_lines = lines[:main_start] + [new_main] + lines[main_end:]
with open('briefing.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('완료')
