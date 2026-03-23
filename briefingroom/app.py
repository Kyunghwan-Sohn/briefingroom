from __future__ import annotations

import json
import os
import time
from datetime import date, timedelta

from briefingroom.config import PDF_DIR, TXT_DIR, DATA_DIR
from briefingroom.crawlers.koreakr import crawl_koreakr
from briefingroom.crawlers.finance import crawl_finance_all
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


def weekly_summary():
    """주간 종합 요약 전용 모드: 각 일별 JSON을 모아 주간 요약 포스팅"""
    today = date.today()
    _, target, target_dates = resolve_targets(today, "weekly", "")

    print("=" * 60)
    print(f"  브리핑룸  |  주간 종합 요약  |  {target_dates[0]} ~ {target_dates[-1]}")
    print("=" * 60)

    # data/ 디렉토리에서 평일 크롤링된 일별 JSON 로드
    all_items = []
    artifacts_dir = DATA_DIR
    for d in target_dates:
        json_path = artifacts_dir / f"{d.isoformat()}.json"
        if not json_path.exists():
            print(f"  ⚠ {d} JSON 없음: {json_path}")
            continue
        data = json.loads(json_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        print(f"  ✓ {d}: {len(items)}건 로드")
        all_items.extend(items)

    if not all_items:
        print("  주간 요약: 데이터 없음")
        return

    print(f"\n총 {len(all_items)}건")

    # 주간 종합 요약 포스팅
    print(f"\n{'─' * 60}")
    print("[주간 종합 요약 포스팅 중...]")
    wp_post_summary(all_items, target, is_weekly=True)

    # 주간 스냅샷 저장
    save_daily_snapshot(all_items, target, is_weekly=True)
    print(f"\n{'=' * 60}")
    print(f"  주간 종합 완료  |  {target}  |  총 {len(all_items)}건")
    print("=" * 60)


def main():
    today = date.today()
    run_mode = os.environ.get("RUN_MODE", "auto")
    run_date = os.environ.get("RUN_DATE", "")

    # weekly-summary 모드: 일별 JSON을 모아 주간 요약만 포스팅
    if run_mode == "weekly-summary":
        weekly_summary()
        return

    is_weekly, target, target_dates = resolve_targets(today, run_mode, run_date)

    print("=" * 60)
    if is_weekly:
        print(f"  브리핑룸 (korea.kr)  |  주간  |  {target_dates[0]} ~ {target_dates[-1]}")
    else:
        print(f"  브리핑룸 (korea.kr)  |  {target}")
    print("=" * 60)

    all_items = []
    for crawl_date in target_dates:
        # 1) korea.kr 통합 크롤링 (정부 부처)
        try:
            items = crawl_koreakr(crawl_date)
            all_items.extend(items)
        except Exception as e:
            print(f"  [korea.kr 오류] {crawl_date}: {str(e)[:80]}")

        # 2) 금융 유관기관 크롤링 (korea.kr 미수록 기관)
        try:
            finance_items = crawl_finance_all(crawl_date)
            all_items.extend(finance_items)
        except Exception as e:
            print(f"  [금융기관 오류] {crawl_date}: {str(e)[:80]}")

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

    # 부처별 통계
    from collections import Counter
    stats = Counter(item["source"] for item in all_items)
    print(f"\n{'─' * 60}")
    for source, cnt in stats.most_common():
        print(f"  ✅ {source:<20} {cnt}건")
    print("─" * 60)
    print(f"  합계: {len(all_items)}건")
    print(f"  파일: {PDF_DIR}")
    print(f"  텍스트: {TXT_DIR}")


if __name__ == "__main__":
    main()
