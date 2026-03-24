from __future__ import annotations

import os
import time
from collections import Counter
from datetime import date

from briefingroom.config import PDF_DIR, TXT_DIR, DATA_DIR
from briefingroom.crawlers.koreakr import crawl_koreakr
from briefingroom.crawlers.finance import crawl_finance_all
from briefingroom.llm import summarize
from briefingroom.pipeline import process_item
from briefingroom.storage import save_daily_snapshot
from briefingroom.wordpress import wp_post


def main():
    today = date.today()
    run_date = os.environ.get("RUN_DATE", "")

    target = today
    if run_date:
        try:
            target = date.fromisoformat(run_date)
        except ValueError:
            pass

    print("=" * 60)
    print(f"  브리핑룸  |  {target}  |  일별 보도자료")
    print("=" * 60)

    # 1) korea.kr 통합 크롤링 (정부 부처)
    all_items = []
    try:
        items = crawl_koreakr(target)
        all_items.extend(items)
    except Exception as e:
        print(f"  [korea.kr 오류] {str(e)[:80]}")

    # 2) 금융 유관기관 크롤링
    try:
        finance_items = crawl_finance_all(target)
        all_items.extend(finance_items)
    except Exception as e:
        print(f"  [금융기관 오류] {str(e)[:80]}")

    print(f"\n{'─' * 60}")
    print(f"총 {len(all_items)}건 수집\n")

    # 파일 처리
    print("[파일 처리 중...]")
    for item in all_items:
        if item["pdfs"] or item["hwps"]:
            process_item(item)

    # LLM 요약
    print(f"\n{'─' * 60}")
    print("[LLM 요약 중...]")
    for item in all_items:
        item["summary"] = summarize(item)
        print(f"  summary: {item['summary'][:60]}")
        time.sleep(0.5)

    # JSON 스냅샷 저장
    snapshot_path = save_daily_snapshot(all_items, target)
    print(f"\n{'─' * 60}")
    print(f"[JSON 저장 완료] {snapshot_path}")

    # WordPress 포스팅
    print(f"\n{'─' * 60}")
    print("[WordPress 포스팅 중...]")
    wp_count = 0
    for item in all_items:
        if wp_post(item):
            wp_count += 1
    print(f"  ✅ WordPress 포스팅 완료: {wp_count}건")

    # 완료 통계
    print(f"\n{'=' * 60}")
    print(f"  완료  |  {target}  |  총 {len(all_items)}건")
    print("=" * 60)

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
