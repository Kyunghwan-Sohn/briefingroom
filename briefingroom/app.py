from __future__ import annotations

import html as _html
import os
import random
import time
from collections import Counter
from datetime import date
from urllib.parse import urlparse

from briefingroom.config import DATA_DIR, NEWS_ENABLED, NEWS_MAX_ITEMS  # noqa: F401
from briefingroom.crawlers.koreakr import crawl_koreakr
from briefingroom.crawlers.finance import crawl_finance_all
from briefingroom.crawlers.president import crawl_president
from briefingroom.crawlers import CRAWLERS
from briefingroom.llm import summarize
from briefingroom.pipeline import process_item
from briefingroom.storage import save_daily_snapshot
from briefingroom.news import get_news_for_item, format_news_html
from briefingroom.verify import verify_counts, fill_missing
from briefingroom.db import init_db, bulk_upsert, bulk_update_wp_status, print_dashboard
from briefingroom.telegram import send_daily_briefing
from briefingroom.static_gen import generate_static


def _safe_html_text(value) -> str:
    return _html.escape(str(value or ""), quote=True)


def _safe_html_url(value) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return _html.escape(url, quote=True)
    return ""


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


def _clean_titles(items: list[dict]) -> int:
    import re as _re

    cleaned = 0
    for item in items:
        orig = item["title"]
        title = orig.replace("\u200b", "").replace("\xa0", " ").replace("&#038;", "&")
        title = _re.sub(r"[\r\n\t]+", " ", title)
        title = _re.sub(r"\s{2,}", " ", title).strip()

        # 제목 반복 제거
        half = len(title) // 2
        if half > 15 and title[:half].strip() == title[half:half * 2].strip():
            title = title[:half].strip()

        # 본문 시작 패턴 이후 제거
        for cut in ["□ ", "○ ", "◈ ", "※ "]:
            idx = title.find(cut)
            if idx > 10:
                title = title[:idx].strip()

        # 부처명(장관 ...) 이후 본문 제거
        title = _re.sub(
            r"(부|청|처|원|위원회|실)\((?:장관|청장|처장|위원장|실장)\s+[\w가-힣]+(?:,\s*이하\s+[\w가-힣]+)?\).*$",
            r"\1", title,
        )

        # "- 부제" 중 본문 시작이면 자르기
        dash_idx = title.find("- ")
        if dash_idx > 10 and len(title) > 80:
            after = title[dash_idx + 2:]
            if _re.match(r"(\d+월|\d{4}년|['']?\d{2}년|지난|올해|금일|오늘|내일)", after):
                title = title[:dash_idx].strip()
            elif len(title) > 120:
                title = title[:dash_idx].strip()

        # 최종 70자 제한
        if len(title) > 70:
            for sep in [", ", "…", "·", " "]:
                cut = title.rfind(sep, 0, 70)
                if cut > 30:
                    title = title[:cut].strip()
                    break
            else:
                title = title[:67] + "..."

        title = title.strip().rstrip(".")
        if title != orig:
            item["title"] = title
            cleaned += 1
    return cleaned


def _env_flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


def _resolve_run_context() -> tuple[date, date, bool, bool, bool, str]:
    today = date.today()
    run_date = os.environ.get("RUN_DATE", "")
    skip_individual = _env_flag("SKIP_INDIVIDUAL", "")
    weekly_enabled = _env_flag("WEEKLY_ENABLED")
    schedule_enabled = _env_flag("SCHEDULE_ENABLED")
    briefing_session = os.environ.get("BRIEFING_SESSION", "").strip().lower()

    target = today
    if run_date:
        try:
            target = date.fromisoformat(run_date)
        except ValueError:
            raise SystemExit(f"RUN_DATE must be YYYY-MM-DD, got: {run_date}")
    return today, target, skip_individual, weekly_enabled, schedule_enabled, briefing_session


def _load_snapshot_items(json_path, target: date) -> list[dict]:
    import json as _json

    print(f"\n  [과거 날짜] {json_path.name} 에서 로드 (크롤링 스킵)")
    data = _json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    for item in items:
        item.setdefault("pdfs", [])
        item.setdefault("hwps", [])
        item.setdefault("files", [])
        item.setdefault("text", "")
        item.setdefault("body_text", "")
    print(f"  {len(items)}건 로드 완료")
    return items


def _crawl_primary_sources(target: date) -> list[dict]:
    all_items = []

    print(f"\n{'━' * 60}")
    print("  Phase 1: korea.kr 통합 크롤링")
    print(f"{'━' * 60}")
    try:
        all_items.extend(crawl_koreakr(target))
    except Exception as e:
        print(f"  [korea.kr 오류] {str(e)[:80]}")

    print(f"\n{'━' * 60}")
    print("  Phase 2: 금융 유관기관 크롤링")
    print(f"{'━' * 60}")
    try:
        all_items.extend(crawl_finance_all(target))
    except Exception as e:
        print(f"  [금융기관 오류] {str(e)[:80]}")

    print(f"\n{'━' * 60}")
    print("  Phase 2-b: 대통령실 크롤링")
    print(f"{'━' * 60}")
    try:
        all_items.extend(crawl_president(target))
    except Exception as e:
        print(f"  [대통령실 오류] {str(e)[:80]}")

    return all_items


def _run_individual_crawlers(target: date, all_items: list[dict]) -> None:
    print(f"\n{'━' * 60}")
    print(f"  Phase 3: 개별 부처 크롤러 ({len(CRAWLERS)}개, 누락분 보완)")
    print(f"{'━' * 60}")

    kr_counts = Counter(item["source"] for item in all_items)
    existing_keys = {(it["title"].strip(), it["date"]) for it in all_items}

    for name, crawler in CRAWLERS:
        try:
            items = crawler(target)
            new_count = 0
            for item in items:
                key = (item["title"].strip(), item["date"])
                if key not in existing_keys:
                    all_items.append(item)
                    existing_keys.add(key)
                    new_count += 1

            kr_cnt = kr_counts.get(name, 0)
            if new_count > 0:
                print(f"  → {name}: +{new_count}건 추가 (korea.kr {kr_cnt}건)")
            else:
                print(f"  → {name}: 추가 없음 (korea.kr {kr_cnt}건으로 완전)")
        except Exception as e:
            print(f"  [{name}] 실패: {str(e)[:60]}")
        time.sleep(random.randint(5, 15))


def _collect_items(today: date, target: date, skip_individual: bool) -> tuple[list[dict], bool]:
    json_path = DATA_DIR / f"{target.isoformat()}.json"
    if target < today and json_path.exists():
        return _load_snapshot_items(json_path, target), True

    all_items = _crawl_primary_sources(target)
    if skip_individual:
        print(f"\n  (SKIP_INDIVIDUAL=true → 개별 부처 크롤링 생략)")
    else:
        _run_individual_crawlers(target, all_items)

    all_items = _dedup(all_items)
    mismatches = verify_counts(all_items, target)
    if mismatches:
        all_items = fill_missing(all_items, mismatches, target)
        all_items = _dedup(all_items)

    print(f"\n{'─' * 60}")
    print("[제목 정제 중...]")
    cleaned = _clean_titles(all_items)
    if cleaned:
        print(f"  제목 정제: {cleaned}건")

    print(f"\n{'─' * 60}")
    print(f"총 {len(all_items)}건 수집 (검증 완료)\n")
    return all_items, False


def _process_and_enrich_items(all_items: list[dict], target: date) -> None:
    init_db()
    bulk_upsert(all_items)
    print(f"[DB 저장] 수집 {len(all_items)}건 → briefingroom.db")

    print(f"\n{'─' * 60}")
    print("[파일 처리 중...]")
    for item in all_items:
        if item.get("text") and len(item.get("text", "")) >= 200:
            continue
        if item.get("pdfs") or item.get("hwps") or item.get("body_text") or item.get("url"):
            process_item(item)
    bulk_upsert(all_items)

    print(f"\n{'─' * 60}")
    print("[LLM 요약 중...]")
    for item in all_items:
        item["summary"] = summarize(item)
        print(f"  summary: {item['summary'][:60]}")
        time.sleep(0.5)
    bulk_upsert(all_items)

    print(f"\n{'─' * 60}")
    print("[관련 뉴스 검색 + 요약 중...]")
    news_count = 0
    news_candidates = all_items[:NEWS_MAX_ITEMS] if NEWS_ENABLED else []
    for item in news_candidates:
        try:
            articles = get_news_for_item(item, llm_fn=summarize)
            if articles:
                item["news_html"] = format_news_html(articles)
                news_count += 1
        except Exception as e:
            print(f"  [뉴스 연결 실패] {item.get('source','')} | {item.get('title','')[:50]} | {e}")
    if NEWS_ENABLED and len(all_items) > len(news_candidates):
        print(f"  [뉴스 검색 제한] 상위 {len(news_candidates)}건만 처리")
    elif not NEWS_ENABLED:
        print("  [뉴스 검색 비활성화] NEWS_ENABLED=false")
    print(f"  관련 뉴스 연결: {news_count}/{len(all_items)}건")

    # ── 법령 연동 ──────────────────────────────────────────
    law_enabled = os.environ.get("LAW_ENABLED", "true").lower() in ("true", "1", "yes")
    if law_enabled:
        print(f"\n{'─' * 60}")
        print("[관련 법령 연동 중...]")
        try:
            from briefingroom.law import process_laws_for_items
            law_count = process_laws_for_items(all_items, max_api_calls=50)
            print(f"  법령 연동: {law_count}건")
        except Exception as e:
            print(f"  [법령 연동 실패] {e}")

    snapshot_path = save_daily_snapshot(all_items, target)
    print(f"\n{'─' * 60}")
    print(f"[JSON 저장 완료] {snapshot_path}")

    print(f"\n{'━' * 60}")
    print("  Phase 5: DB 기반 최종 점검 (포스팅 전)")
    print(f"{'━' * 60}")
    bulk_upsert(all_items)
    _db_audit(target)


def _run_wordpress(all_items: list[dict], target: date) -> None:
    wp_enabled = _env_flag("WP_ENABLED")
    if not wp_enabled:
        print(f"\n{'─' * 60}")
        print("  (WP_ENABLED=false → WordPress 포스팅 스킵)")
        return

    from briefingroom.wordpress import wp_post

    print(f"\n{'─' * 60}")
    print("[WordPress 포스팅 중...]")
    wp_count = 0
    wp_updates = []
    for item in all_items:
        try:
            result = wp_post(item)
            if result:
                wp_count += 1
                if isinstance(result, tuple):
                    post_id, post_link = result
                else:
                    post_id, post_link = (result if isinstance(result, int) else 0), ""
                item["wp_post_id"] = post_id
                item["wp_link"] = post_link
                wp_updates.append((item["date"], item["title"], item["source"], post_id, "ok"))
            else:
                wp_updates.append((item["date"], item["title"], item["source"], 0, "skipped"))
        except Exception as e:
            print(f"  [WP 실패] {item.get('source','')} | {item.get('title','')[:50]} | {e}")
            wp_updates.append((item["date"], item["title"], item["source"], 0, "failed"))
    bulk_update_wp_status(wp_updates)
    print(f"  ✅ WordPress 포스팅 완료: {wp_count}건")

    print(f"\n{'─' * 60}")
    print("[실패 건 재처리: 요약 없는 포스트 보완]")
    _retry_missing_summaries(target)
    bulk_upsert(all_items)


def _run_instagram(target: date) -> None:
    ig_enabled = _env_flag("INSTAGRAM_ENABLED")
    ig_image_only = _env_flag("INSTAGRAM_IMAGE_ONLY")
    if not (ig_enabled or ig_image_only):
        print(f"\n{'─' * 60}")
        print("  (INSTAGRAM_ENABLED=false → 인스타그램 스킵)")
        return

    from briefingroom.instagram_image import generate_daily_carousels
    from briefingroom.instagram import post_daily_carousels

    print(f"\n{'━' * 60}")
    print("  Phase 7: 인스타그램 캐러셀 이미지 생성")
    print(f"{'━' * 60}")
    carousel_results = generate_daily_carousels(target)
    if carousel_results:
        post_daily_carousels(carousel_results, target)
    else:
        print("  [Instagram] 생성할 캐러셀 없음")


def _run_notifications(all_items: list[dict], target: date, is_saturday: bool, briefing_session: str) -> None:
    if is_saturday:
        from briefingroom.weekly import run_weekly

        print(f"\n{'━' * 60}")
        print("  Phase 8: 주간 보도자료 요약 (월~토)")
        print(f"{'━' * 60}")
        run_weekly(target)
        return
    send_daily_briefing(all_items, target, session=briefing_session)


def main():
    today, target, skip_individual, weekly_enabled, schedule_enabled, briefing_session = _resolve_run_context()

    # ── 일요일: 크롤링 없이 차주 정부 일정만 ──
    if (schedule_enabled or target.weekday() == 6) and not weekly_enabled:
        print("=" * 60)
        print(f"  브리핑룸  |  {target}  |  차주 정부 일정 (일요일)")
        print("=" * 60)
        from briefingroom.schedule import run_schedule
        run_schedule(target)
        return

    is_saturday = weekly_enabled or target.weekday() == 5
    mode = "토요일 크롤링 + 주간 요약" if is_saturday else "일별 보도자료"

    print("=" * 60)
    print(f"  브리핑룸  |  {target}  |  {mode}")
    print("=" * 60)

    all_items, loaded_from_snapshot = _collect_items(today, target, skip_individual)
    if not loaded_from_snapshot:
        _process_and_enrich_items(all_items, target)
    _run_wordpress(all_items, target)
    generate_static(target.isoformat())

    print(f"\n{'━' * 60}")
    print("  Phase 6: 최종 점검")
    print(f"{'━' * 60}")
    _db_audit(target)

    _run_instagram(target)
    _run_notifications(all_items, target, is_saturday, briefing_session)

    # ── 지원사업 수집 (매일 1회) ──
    subsidy_enabled = _env_flag("SUBSIDY_ENABLED", "true")
    if subsidy_enabled and not is_saturday:
        try:
            from briefingroom.subsidy import run_subsidy
            run_subsidy()
        except Exception as e:
            print(f"  [지원사업 수집 실패] {e}")

    print_dashboard(target.isoformat())
    print_dashboard()


def _retry_missing_summaries(target):
    """WP에서 해당 날짜의 요약 없는 포스트를 찾아 원문에서 본문 추출 → LLM → 업데이트"""
    import re
    from bs4 import BeautifulSoup

    from briefingroom.http import build_session
    from briefingroom.wordpress import WP_URL, WP_USER, WP_PASS

    if not WP_USER:
        print("  (WP 인증 없음 → 스킵)")
        return

    auth = (WP_USER, WP_PASS)
    s = build_session(retries=2)

    ds = target.isoformat()
    no_summary = []
    list_failed = False

    for pg in range(1, 10):
        try:
            r = s.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={
                    "per_page": 100,
                    "page": pg,
                    "status": "publish",
                    "after": f"{ds}T00:00:00",
                    "before": f"{ds}T23:59:59",
                    "_fields": "id,title,content",
                },
                auth=auth,
                timeout=15,
            )
            payload = r.json() if r.status_code == 200 else []
        except Exception as e:
            print(f"  [WP 요약 재조회 실패] page={pg} | {e}")
            list_failed = True
            break
        if r.status_code != 200 or not payload:
            break
        for p in payload:
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
        if len(payload) < 100:
            break

    if list_failed and not no_summary:
        print("  요약 재처리 중단: WP 목록 조회 실패")
        return
    if not no_summary:
        print("  요약 미완료 건 없음 ✅")
        return

    print(f"  요약 미완료 {len(no_summary)}건 발견 → 재처리")
    updated = 0
    fetch_failed = 0
    update_failed = 0
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
        except Exception as e:
            fetch_failed += 1
            print(f"    [원문 재수집 실패] #{item['id']} | {e}")
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

        safe_summary = _safe_html_text(summary_text)
        new_content = re.sub(
            r'(<div class="briefing-summary">.*?<p>)[^<]*(</p>)',
            rf'\g<1>{safe_summary}\g<2>',
            item["content"], flags=re.DOTALL
        )
        kw_html = (
            '<div class="briefing-keywords">' +
            " ".join(f"<span>#{_safe_html_text(k)}</span>" for k in keywords if k) +
            "</div>"
        ) if keywords else ""
        if kw_html and '<div class="briefing-keywords">' in new_content:
            new_content = re.sub(r'<div class="briefing-keywords">.*?</div>', kw_html, new_content)

        try:
            r = s.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{item['id']}",
                json={"content": new_content},
                auth=auth,
                timeout=15,
            )
        except Exception as e:
            update_failed += 1
            print(f"    [WP 요약 업데이트 실패] #{item['id']} | {e}")
            continue
        if r.status_code == 200:
            updated += 1
            print(f"    ✅ #{item['id']} {item['source']}: 요약 보완 완료")
        else:
            update_failed += 1
            print(f"    [WP 요약 업데이트 실패] #{item['id']} | HTTP {r.status_code}")
        time.sleep(0.5)

    print(f"  재처리 완료: {updated}/{len(no_summary)}건 보완 (원문실패 {fetch_failed}건, 업데이트실패 {update_failed}건)")


def _db_audit(target):
    """DB 기반 최종 점검: 제목/파일/LLM/WP 상태 검증"""
    import sqlite3
    from briefingroom.db import DB_PATH

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    ds = target.isoformat()

    total = conn.execute("SELECT COUNT(*) FROM articles WHERE date=?", (ds,)).fetchone()[0]
    if total == 0:
        print(f"  DB에 {ds} 데이터 없음")
        conn.close()
        return

    # 제목 점검
    long_titles = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND LENGTH(title) > 120", (ds,)).fetchone()[0]
    short_titles = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND LENGTH(title) < 10", (ds,)).fetchone()[0]

    # 파일 점검
    file_ok = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND file_status='ok'", (ds,)).fetchone()[0]
    file_fail = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND file_status='failed'", (ds,)).fetchone()[0]
    file_none = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND file_status='no_file'", (ds,)).fetchone()[0]

    # LLM 점검
    llm_ok = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND llm_status='ok'", (ds,)).fetchone()[0]
    llm_fail = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND llm_status='failed'", (ds,)).fetchone()[0]
    llm_pend = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND llm_status='pending'", (ds,)).fetchone()[0]

    # WP 점검
    wp_ok = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND wp_status='ok'", (ds,)).fetchone()[0]
    wp_skip = conn.execute("SELECT COUNT(*) FROM articles WHERE date=? AND wp_status='skipped'", (ds,)).fetchone()[0]

    conn.close()

    llm_pct = llm_ok / total * 100 if total else 0
    wp_pct = wp_ok / total * 100 if total else 0

    print(f"\n  ┌─ {ds} 최종 점검 결과 ─────────────────────┐")
    print(f"  │ 총 수집:    {total:>5}건                        │")
    print(f"  │                                              │")
    print(f"  │ 제목:       정상 {total-long_titles-short_titles}건 | 긴제목 {long_titles} | 짧은제목 {short_titles}  │")
    print(f"  │ 파일:       추출성공 {file_ok} | 실패 {file_fail} | 없음 {file_none}      │")
    print(f"  │ LLM 요약:   ✅{llm_ok} | ❌{llm_fail} | ⏳{llm_pend} ({llm_pct:.0f}%)     │")
    print(f"  │ WP 포스팅:  ✅{wp_ok} | ⏭{wp_skip} ({wp_pct:.0f}%)              │")

    issues = []
    if long_titles > 0:
        issues.append(f"긴 제목 {long_titles}건")
    if short_titles > 0:
        issues.append(f"짧은 제목 {short_titles}건")
    if file_fail > 0:
        issues.append(f"파일 추출 실패 {file_fail}건")
    if llm_fail > 0:
        issues.append(f"LLM 실패 {llm_fail}건")
    if llm_pend > 0:
        issues.append(f"LLM 미처리 {llm_pend}건")

    if issues:
        print(f"  │                                              │")
        print(f"  │ ⚠️ 이슈: {', '.join(issues):<36} │")
    else:
        print(f"  │                                              │")
        print(f"  │ ✅ 모든 항목 정상                             │")

    print(f"  └──────────────────────────────────────────────┘")


if __name__ == "__main__":
    main()
