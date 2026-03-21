with open('briefing.py', encoding='utf-8') as f:
    lines = f.readlines()

start = next(i for i,l in enumerate(lines) if '    all_items = []' in l)
end = start + 1
while end < len(lines):
    if '    time.sleep(random.randint(30, 90))' in lines[end]:
        end += 1
        break
    end += 1

new_block = '''    all_items = []
    MAX_RETRY = 3

    for crawl_date in target_dates:
        if is_weekly:
            print(f"\\n{'='*40}  {crawl_date}  {'='*40}")

        failed = []

        # 1차 수집
        for name, crawler in CRAWLERS:
            try:
                items = crawler(crawl_date)
                print(f"  \u2192 {name}: {len(items)}\uac74")
                all_items.extend(items)
            except Exception as e:
                print(f"  [{name}] \uc2e4\ud328: {str(e)[:80]}")
                failed.append((name, crawler))
            time.sleep(random.randint(30, 90))

        # \uc7ac\uc2dc\ub3c4
        retry_count = 0
        while failed and retry_count < MAX_RETRY:
            retry_count += 1
            print(f"\\n{'='*60}")
            print(f"  \uc2e4\ud328 \ubd80\uc218 {len(failed)}\uac1c \u2192 30\ubd84 \ud6c4 \uc7ac\uc2dc\ub3c4 ({retry_count}/{MAX_RETRY})")
            print(f"  \ub300\uc0c1: {', '.join(n for n,_ in failed)}")
            print(f"{'='*60}")
            time.sleep(1800)

            still_failed = []
            for name, crawler in failed:
                try:
                    items = crawler(crawl_date)
                    print(f"  \u2192 [{name}] \uc7ac\uc2dc\ub3c4 \uc131\uacf5: {len(items)}\uac74")
                    all_items.extend(items)
                except Exception as e:
                    print(f"  [{name}] \uc7ac\uc2dc\ub3c4 \uc2e4\ud328: {str(e)[:80]}")
                    still_failed.append((name, crawler))
                time.sleep(random.randint(30, 90))
            failed = still_failed

        if failed:
            print(f"\\n  \ucd5c\uc885 \uc2e4\ud328: {', '.join(n for n,_ in failed)}")
        else:
            print(f"\\n  \u2705 \ubaa8\ub4e0 \ubd80\uc218 \uc218\uc9d1 \uc644\ub8cc!")

'''

new_lines = lines[:start] + [new_block] + lines[end:]
with open('briefing.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('완료')

# 확인
with open('briefing.py', encoding='utf-8') as f:
    content = f.read()
idx = content.find('all_items = []')
print(content[idx:idx+300])
