from __future__ import annotations

import os
import random
import time
from collections import Counter
from datetime import date

from briefingroom.config import PDF_DIR, TXT_DIR, DATA_DIR
from briefingroom.crawlers.koreakr import crawl_koreakr
from briefingroom.crawlers.finance import crawl_finance_all
from briefingroom.crawlers import CRAWLERS
from briefingroom.llm import summarize
from briefingroom.pipeline import process_item
from briefingroom.storage import save_daily_snapshot
from briefingroom.wordpress import wp_post


def _dedup(items: list[dict]) -> list[dict]:
    """제목+날짜 기준 중복 제거 (먼저 들어온 것 유지)"""
    seen = set()
    unique = []
    for item in items:
        key = (item["title"].strip(), item["date"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    removed = len(items) - len(unique)
    if removed:
        print(f"  [중복 제거] {removed}건")
    return unique


def main():
    today = date.today()
    run_date = os.environ.get("RUN_DATE", "")
    skip_individual = os.environ.get("SKIP_INDIVIDUAL", "").lower() in ("1", "true", "yes")

    target = today
    if run_date:
        try:
            target = date.fromisoformat(run_date)
        except ValueError:
            pass

    print("=" * 60)
    print(f"  브리핑룸  |  {target}  |  일별 보도자료")
    print("=" * 60)

    all_items = []

    # ── Phase 1: korea.kr (빠름, IP 차단 없음) ──────────────
    print(f"\n{'━' * 60}")
    print("  Phase 1: korea.kr 통합 크롤링")
    print(f"{'━' * 60}")
    try:
        items = crawl_koreakr(target)
        all_items.extend(items)
    except Exception as e:
        print(f"  [korea.kr 오류] {str(e)[:80]}")

    # ── Phase 2: 금융 유관기관 (korea.kr 미수록) ─────────────
    print(f"\n{'━' * 60}")
    print("  Phase 2: 금융 유관기관 크롤링")
    print(f"{'━' * 60}")
    try:
        finance_items = crawl_finance_all(target)
        all_items.extend(finance_items)
    except Exception as e:
        print(f"  [금융기관 오류] {str(e)[:80]}")

    # ── Phase 3: 개별 부처 크롤러 (누락분 보완) ──────────────
    if not skip_individual:
        print(f"\n{'━' * 60}")
        print(f"  Phase 3: 개별 부처 크롤러 ({len(CRAWLERS)}개, 누락분 보완)")
        print(f"{'━' * 60}")

        # korea.kr에서 이미 수집된 부처별 건수
        kr_counts = Counter(item["source"] for item in all_items)

        for name, crawler in CRAWLERS:
            try:
                items = crawler(target)
                new_count = 0
                for item in items:
                    # 이미 수집된 제목이면 스킵
                    key = (item["title"].strip(), item["date"])
                    existing = any(
                        (it["title"].strip(), it["date"]) == key for it in all_items
                    )
                    if not existing:
                        all_items.append(item)
                        new_count += 1

                kr_cnt = kr_counts.get(name, 0)
                if new_count > 0:
                    print(f"  → {name}: +{new_count}건 추가 (korea.kr {kr_cnt}건)")
                else:
                    print(f"  → {name}: 추가 없음 (korea.kr {kr_cnt}건으로 완전)")
            except Exception as e:
                print(f"  [{name}] 실패: {str(e)[:60]}")
            time.sleep(random.randint(5, 15))
    else:
        print(f"\n  (SKIP_INDIVIDUAL=true → 개별 부처 크롤링 생략)")

    # ── 최종 중복 제거 ───────────────────────────────────────
    all_items = _dedup(all_items)

    print(f"\n{'─' * 60}")
    print(f"총 {len(all_items)}건 수집\n")

    # ── 파일 처리 ────────────────────────────────────────────
    print("[파일 처리 중...]")
    for item in all_items:
        if item["pdfs"] or item["hwps"]:
            process_item(item)

    # ── LLM 요약 ─────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("[LLM 요약 중...]")
    for item in all_items:
        item["summary"] = summarize(item)
        print(f"  summary: {item['summary'][:60]}")
        time.sleep(0.5)

    # ── JSON 스냅샷 저장 ──────────────────────────────────────
    snapshot_path = save_daily_snapshot(all_items, target)
    print(f"\n{'─' * 60}")
    print(f"[JSON 저장 완료] {snapshot_path}")

    # ── WordPress 포스팅 ──────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("[WordPress 포스팅 중...]")
    wp_count = 0
    for item in all_items:
        if wp_post(item):
            wp_count += 1
    print(f"  ✅ WordPress 포스팅 완료: {wp_count}건")

    # ── 완료 통계 ─────────────────────────────────────────────
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
