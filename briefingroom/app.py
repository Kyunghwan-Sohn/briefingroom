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

    # ── 실패 건 재처리 (요약 없는 포스트 보완) ─────────────────
    print(f"\n{'─' * 60}")
    print("[실패 건 재처리: 요약 없는 포스트 보완]")
    _retry_missing_summaries(target)

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


def _retry_missing_summaries(target):
    """WP에서 해당 날짜의 요약 없는 포스트를 찾아 원문에서 본문 추출 → LLM → 업데이트"""
    import html as _html
    import re
    import requests
    import ssl
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context

    class _TLS(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            ctx = create_urllib3_context()
            ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            kwargs["ssl_context"] = ctx
            return super().init_poolmanager(*args, **kwargs)

    from briefingroom.wordpress import WP_URL, WP_USER, WP_PASS

    if not WP_USER:
        print("  (WP 인증 없음 → 스킵)")
        return

    auth = (WP_USER, WP_PASS)
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    s.mount("https://", _TLS(max_retries=2))

    ds = target.isoformat()
    no_summary = []

    for pg in range(1, 10):
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts",
                         params={"per_page": 100, "page": pg, "status": "publish",
                                 "after": f"{ds}T00:00:00", "before": f"{ds}T23:59:59",
                                 "_fields": "id,title,content"},
                         auth=auth, timeout=15)
        if r.status_code != 200 or not r.json():
            break
        for p in r.json():
            content = p.get("content", {}).get("rendered", "")
            sum_m = re.search(r'briefing-summary.*?<p>([^<]+)', content, re.DOTALL)
            summary = sum_m.group(1).strip() if sum_m else ""
            if not summary or "보도자료입니다. 원문 링크에서" in summary:
                orig_m = re.search(r'href="([^"]+)"[^>]*>↗\s*원문', content)
                src_m = re.search(r'briefing-source[^>]*>🏛\s*([^<]+)', content)
                no_summary.append({
                    "id": p["id"],
                    "title": _html.unescape(p["title"]["rendered"]),
                    "source": src_m.group(1).strip() if src_m else "",
                    "url": _html.unescape(orig_m.group(1)) if orig_m else "",
                    "content": content,
                })
        if len(r.json()) < 100:
            break

    if not no_summary:
        print("  요약 미완료 건 없음 ✅")
        return

    print(f"  요약 미완료 {len(no_summary)}건 발견 → 재처리")
    updated = 0
    for item in no_summary:
        url = item["url"]
        if not url:
            continue
        body_text = ""
        try:
            r = s.get(url, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                for sel in ["div.view_cont", "div.article_view", "article", "div.content", "main"]:
                    el = soup.select_one(sel)
                    if el and len(el.get_text(strip=True)) > 50:
                        body_text = re.sub(r"\s+", " ", el.get_text(strip=True))[:6000]
                        break
                if not body_text:
                    og = soup.find("meta", property="og:description")
                    if og and og.get("content") and len(og["content"]) > 30:
                        body_text = og["content"]
        except Exception:
            continue

        if not body_text or len(body_text) < 30:
            continue

        result = summarize({"source": item["source"], "title": item["title"], "text": body_text})
        if result.startswith("["):
            continue

        summary_text = ""
        keywords = []
        for line in result.split("\n"):
            if line.startswith("요약:"):
                summary_text = line.replace("요약:", "").strip()
            elif line.startswith("키워드:"):
                keywords = [k.strip() for k in line.replace("키워드:", "").split(",")]
        if not summary_text:
            summary_text = result

        new_content = re.sub(
            r'(<div class="briefing-summary">.*?<p>)[^<]*(</p>)',
            rf'\g<1>{summary_text}\g<2>',
            item["content"], flags=re.DOTALL
        )
        kw_html = '<div class="briefing-keywords">' + " ".join(f"<span>#{k}</span>" for k in keywords) + "</div>" if keywords else ""
        if kw_html and '<div class="briefing-keywords">' in new_content:
            new_content = re.sub(r'<div class="briefing-keywords">.*?</div>', kw_html, new_content)

        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts/{item['id']}",
                          json={"content": new_content}, auth=auth, timeout=15)
        if r.status_code == 200:
            updated += 1
            print(f"    ✅ #{item['id']} {item['source']}: 요약 보완 완료")
        time.sleep(0.5)

    print(f"  재처리 완료: {updated}/{len(no_summary)}건 보완")


if __name__ == "__main__":
    main()
