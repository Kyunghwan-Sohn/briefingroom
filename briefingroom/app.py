from __future__ import annotations

import os
import random
import time
from datetime import date, timedelta

from briefingroom.config import PDF_DIR, TXT_DIR, RETRY_DELAYS, CRAWL_DELAY_MIN, CRAWL_DELAY_MAX
from briefingroom.crawlers import CRAWLERS, CRAWLER_ALIASES
from briefingroom.llm import summarize
from briefingroom.pipeline import process_item
from briefingroom.storage import save_daily_snapshot
from briefingroom.wordpress import wp_post, wp_post_summary


def resolve_targets(today: date, run_mode: str, run_date: str):
    weekday = today.weekday()
    if run_mode == "weekly":
        is_weekly = True
    elif run_mode == "daily":
        is_weekly = False
    else:
        is_weekly = weekday in (5, 6)

    if is_weekly:
        last_friday = today
        while last_friday.weekday() != 4:
            last_friday -= timedelta(days=1)
        last_monday = last_friday - timedelta(days=4)
        target_dates = [last_monday + timedelta(days=i) for i in range(5)]
        target = last_friday
    else:
        target = today
        if run_date:
            try:
                target = date.fromisoformat(run_date)
            except ValueError:
                pass
        target_dates = [target]

    return is_weekly, target, target_dates


def resolve_selected_crawlers(selected_raw: str):
    if not selected_raw.strip():
        return CRAWLERS

    requested = [part.strip() for part in selected_raw.split(",") if part.strip()]
    selected_names = []
    missing = []

    for item in requested:
        if item in dict(CRAWLERS):
            selected_names.append(item)
            continue

        alias_target = CRAWLER_ALIASES.get(item.lower())
        if alias_target:
            selected_names.append(alias_target)
            continue

        missing.append(item)

    if missing:
        print(f"[경고] 알 수 없는 부처/코드: {', '.join(missing)}")

    selected_names = list(dict.fromkeys(selected_names))
    if not selected_names:
        print("[경고] 선택된 부처가 없어 전체 부처를 실행합니다.")
        return CRAWLERS

    return [(name, crawler) for name, crawler in CRAWLERS if name in selected_names]


def main():
    today = date.today()
    run_mode = os.environ.get("RUN_MODE", "auto")
    run_date = os.environ.get("RUN_DATE", "")
    is_weekly, target, target_dates = resolve_targets(today, run_mode, run_date)
    selected_raw = os.environ.get("CRAWLER_SOURCES", "")
    selected_crawlers = resolve_selected_crawlers(selected_raw)

    print("=" * 60)
    if is_weekly:
        print(f"  브리핑룸  |  주간 모음  |  {target_dates[0]} ~ {target_dates[-1]}")
    else:
        print(f"  브리핑룸  |  {target}  |  {len(selected_crawlers)}개 부처")
    print("=" * 60)
    if selected_raw.strip():
        print("  선택 실행: " + ", ".join(name for name, _ in selected_crawlers))

    all_items = []
    collected_keys = set()  # 중복 방지: (source, title, date)

    # 주간 모드: 부처 간 딜레이 축소 (5일 × 26부처 = 130회이므로)
    delay_min = 10 if is_weekly else CRAWL_DELAY_MIN
    delay_max = 30 if is_weekly else CRAWL_DELAY_MAX

    for crawl_date in target_dates:
        if is_weekly:
            print(f"\n{'=' * 40}  {crawl_date}  {'=' * 40}")

        failed = []
        for name, crawler in selected_crawlers:
            try:
                items = crawler(crawl_date)
                # 중복 방지: 재시도 시 이미 수집된 항목 제외
                new_items = []
                for item in items:
                    key = (item["source"], item["title"], item["date"])
                    if key not in collected_keys:
                        collected_keys.add(key)
                        new_items.append(item)
                print(f"  → {name}: {len(new_items)}건")
                all_items.extend(new_items)
            except Exception as e:
                print(f"  [{name}] 실패: {str(e)[:80]}")
                failed.append((name, crawler))
            time.sleep(random.randint(delay_min, delay_max))

        # 점진적 백오프 재시도: 5분 → 10분 → 15분 (총 30분, 기존 90분에서 대폭 축소)
        for retry_idx, wait_sec in enumerate(RETRY_DELAYS):
            if not failed:
                break
            wait_min = wait_sec // 60
            print(f"\n{'=' * 60}")
            print(f"  실패 부처 {len(failed)}개 → {wait_min}분 후 재시도 ({retry_idx+1}/{len(RETRY_DELAYS)})")
            print(f"  대상: {', '.join(n for n, _ in failed)}")
            print("=" * 60)
            time.sleep(wait_sec)

            still_failed = []
            for name, crawler in failed:
                try:
                    items = crawler(crawl_date)
                    new_items = []
                    for item in items:
                        key = (item["source"], item["title"], item["date"])
                        if key not in collected_keys:
                            collected_keys.add(key)
                            new_items.append(item)
                    print(f"  → [{name}] 재시도 성공: {len(new_items)}건")
                    all_items.extend(new_items)
                except Exception as e:
                    print(f"  [{name}] 재시도 실패: {str(e)[:80]}")
                    still_failed.append((name, crawler))
                time.sleep(random.randint(delay_min, delay_max))
            failed = still_failed

        if failed:
            print(f"\n  최종 실패: {', '.join(n for n, _ in failed)}")
        else:
            print("\n  ✅ 모든 부처 수집 완료!")

    print(f"\n{'─' * 60}")
    print(f"총 {len(all_items)}건 수집\n")

    print("[파일 처리 중...]")
    for item in all_items:
        if item["pdfs"] or item["hwps"]:
            process_item(item)

    print(f"\n{'─' * 60}")
    print("[LLM 요약 중...]")
    for item in all_items:
        item["summary"] = summarize(item)
        print(f"  summary: {item['summary'][:60]}")
        time.sleep(0.5)

    snapshot_path = save_daily_snapshot(all_items, target, is_weekly=is_weekly)
    print(f"\n{'─' * 60}")
    print(f"[JSON 저장 완료] {snapshot_path}")

    print(f"\n{'─' * 60}")
    print("[WordPress 포스팅 중...]")
    wp_count = 0
    for item in all_items:
        if wp_post(item):
            wp_count += 1
    print(f"  ✅ WordPress 포스팅 완료: {wp_count}건")

    print(f"\n{'─' * 60}")
    print("[종합 요약 포스팅 중...]")
    wp_post_summary(all_items, target, is_weekly)

    print(f"\n{'=' * 60}")
    print(f"  완료  |  {target}  |  총 {len(all_items)}건")
    print("=" * 60)
    if selected_raw.strip():
        print("  선택 실행: " + ", ".join(name for name, _ in selected_crawlers))

    print(f"\n{'─' * 60}")
    for name, _ in selected_crawlers:
        cnt = sum(1 for i in all_items if i["source"] == name)
        mark = "✅" if cnt > 0 else "⚪"
        print(f"  {mark} {name:<20} {cnt}건")
    print("─" * 60)
    print(f"  합계: {len(all_items)}건")
    print(f"  파일: {PDF_DIR}")
    print(f"  텍스트: {TXT_DIR}")


if __name__ == "__main__":
    main()
