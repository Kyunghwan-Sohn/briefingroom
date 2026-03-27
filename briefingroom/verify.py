"""포스팅 전 검증: 기관별 실제 보도자료 수 vs 수집 수 비교

각 기관의 웹사이트에서 실제 보도자료 개수를 확인하고,
수집 건수와 비교하여 누락분을 재크롤링합니다.
"""
from __future__ import annotations

import re
import time
from collections import Counter
from datetime import date

import requests
from bs4 import BeautifulSoup

from briefingroom.config import VERIFY_FINANCE_PLAYWRIGHT
from briefingroom.http import build_session


def _session():
    return build_session(
        retries=2,
        legacy_tls_prefixes=(
            "https://www.korea.kr/",
            "https://www.fss.or.kr/",
        ),
    )


# ═══════════════════════════════════════════════════════════
# 기관별 실제 건수 확인 함수
# ═══════════════════════════════════════════════════════════

def _count_koreakr(s, target: date, source_name: str) -> tuple[int, list[str]]:
    """korea.kr에서 특정 부처의 해당 날짜 보도자료 건수 + 제목 목록"""
    ds = target.isoformat()
    titles = []
    for pg in range(1, 15):
        try:
            r = s.get(f"https://www.korea.kr/briefing/pressReleaseList.do"
                      f"?pageIndex={pg}&startDate={ds}&endDate={ds}", timeout=15)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "lxml")
            found = 0
            for li in soup.find_all("li"):
                a = li.find("a", href=lambda h: h and "pressReleaseView" in h)
                if not a:
                    continue
                spans = [sp.get_text(strip=True) for sp in li.find_all("span") if sp.get_text(strip=True)]
                src = None
                for sp in reversed(spans):
                    if re.match(r"^[\w가-힣]{2,}$", sp) and not re.match(r"^\d", sp):
                        src = sp
                        break
                if src == source_name:
                    # 제목 추출
                    text_span = a.find("span", class_="text")
                    lead_span = a.find("span", class_="lead")
                    if text_span and lead_span:
                        full = text_span.get_text(strip=True)
                        lead = lead_span.get_text(strip=True)
                        idx = full.find(lead[:30]) if lead else -1
                        title = full[:idx].strip() if idx > 5 else full[:80]
                    elif text_span:
                        title = text_span.get_text(strip=True)[:80]
                    else:
                        title = a.get_text(strip=True)[:80]
                    titles.append(title)
                    found += 1
            if found == 0 and pg > 2:
                break
        except Exception:
            break
    return len(titles), titles


def _count_fss(s, target: date) -> int:
    """금융감독원 실제 건수"""
    count = 0
    ds = target.isoformat()
    for pg in range(1, 5):
        try:
            r = s.get(f"https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218&pageIndex={pg}", timeout=15)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "lxml")
            for row in soup.select("table tbody tr"):
                text = row.get_text(" ", strip=True)
                dm = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                if dm:
                    rd = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                    if rd == ds:
                        count += 1
                    elif rd < ds:
                        return count
        except Exception:
            break
    return count


def _count_bok(s, target: date) -> int:
    """한국은행 — Playwright 필요, requests로는 0 반환되므로 Playwright 시도"""
    try:
        from playwright.sync_api import sync_playwright
        count = 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", locale="ko-KR")
            page = ctx.new_page()
            page.goto("https://www.bok.or.kr/portal/singl/newsData/list.do?menuNo=201263", wait_until="networkidle", timeout=20000)
            soup = BeautifulSoup(page.content(), "lxml")
            for a in soup.find_all("a", class_="title"):
                parent = a
                date_span = None
                for _ in range(5):
                    parent = parent.find_parent()
                    if not parent: break
                    date_span = parent.find("span", class_="date")
                    if date_span: break
                if date_span:
                    dt = re.sub(r"등록일", "", date_span.get_text(strip=True))
                    dm = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", dt)
                    if dm and f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" == target.isoformat():
                        count += 1
            browser.close()
        return count
    except Exception:
        return 0


def _count_krx(s, target: date) -> int:
    """한국거래소 — Playwright"""
    try:
        from playwright.sync_api import sync_playwright
        count = 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", locale="ko-KR")
            page = ctx.new_page()
            page.goto("https://open.krx.co.kr/contents/OPN/05/05000000/OPN05000000.jsp", wait_until="networkidle", timeout=20000)
            soup = BeautifulSoup(page.content(), "lxml")
            ds = target.isoformat()
            seen = set()
            for el in soup.find_all(["li", "div"]):
                text = el.get_text(" ", strip=True)
                dm = re.search(r"(\d{4})[/.\-](\d{2})[/.\-](\d{2})", text)
                if not dm: continue
                if f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" != ds: continue
                a = el.find("a")
                if a:
                    t = a.get_text(strip=True)
                    if t and len(t) > 5 and t not in seen:
                        seen.add(t)
                        count += 1
            browser.close()
        return count
    except Exception:
        return 0


def _count_kdic(s, target: date) -> int:
    """예금보험공사 — Playwright 메인 페이지"""
    try:
        from playwright.sync_api import sync_playwright
        count = 0
        ds = target.isoformat()
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            page.goto("https://www.kdic.or.kr", wait_until="networkidle", timeout=20000)
            soup = BeautifulSoup(page.content(), "lxml")
            for a in soup.find_all("a"):
                text = a.get_text(strip=True)
                dm = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                if dm and f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" == ds:
                    title = re.sub(r"\d{4}[.\-]\d{2}[.\-]\d{2}.*$", "", text).strip()
                    if title and len(title) > 5 and "입찰" not in title and "공용차량" not in title:
                        count += 1
            browser.close()
        return count
    except Exception:
        return 0


def _count_kfb(s, target: date) -> int:
    """은행연합회 — Playwright 메인 페이지"""
    try:
        from playwright.sync_api import sync_playwright
        count = 0
        ds = target.isoformat()
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            page.goto("https://www.kfb.or.kr", wait_until="networkidle", timeout=20000)
            soup = BeautifulSoup(page.content(), "lxml")
            for a in soup.find_all("a", href=re.compile(r"info_news_view")):
                parent = a.find_parent()
                ptext = parent.get_text(" ", strip=True) if parent else ""
                dm = re.search(r"(\d{4})[/.\-](\d{2})[/.\-](\d{2})", ptext)
                if dm and f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" == ds:
                    count += 1
            browser.close()
        return count
    except Exception:
        return 0


# 금융기관 검증 함수 목록
FINANCE_VERIFIERS = [
    ("금융감독원",   _count_fss),
    ("한국은행",     _count_bok),
    ("한국거래소",   _count_krx),
    ("예금보험공사", _count_kdic),
    ("은행연합회",   _count_kfb),
]


# 검증 가능한 기관 목록 (korea.kr에서 확인 가능)
VERIFIABLE_SOURCES = [
    "금융위원회", "기획재정부", "재정경제부", "교육부", "보건복지부",
    "고용노동부", "국토교통부", "외교부", "과학기술정보통신부", "행정안전부",
    "산업통상자원부", "산업통상부", "농림축산식품부", "문화체육관광부",
    "법무부", "국방부", "환경부", "기후에너지환경부", "해양수산부",
    "중소벤처기업부", "통일부", "경찰청", "소방청", "산림청",
]


def verify_counts(items: list[dict], target: date) -> dict:
    """수집 건수 vs 실제 건수 비교. 누락 기관 리스트 반환."""
    print(f"\n{'━' * 60}")
    print(f"  검증: 기관별 수집 건수 vs 실제 건수")
    print(f"{'━' * 60}")

    s = _session()
    collected = Counter(item["source"] for item in items)
    mismatches = {}  # source → (collected, actual)

    # 주요 기관 korea.kr 대비 검증 (건수 + 제목)
    collected_titles = {}
    for item in items:
        src = item.get("source", "")
        if src not in collected_titles:
            collected_titles[src] = set()
        collected_titles[src].add(item.get("title", "").strip()[:50])

    for source in VERIFIABLE_SOURCES:
        my_count = collected.get(source, 0)
        try:
            actual_count, actual_titles = _count_koreakr(s, target, source)
            diff = actual_count - my_count
            if diff > 0:
                mismatches[source] = (my_count, actual_count)
                # 누락 제목 식별
                my_titles = collected_titles.get(source, set())
                missing = [t for t in actual_titles if t[:50] not in my_titles]
                print(f"  ⚠️  {source:<18} 수집 {my_count}건 / 실제 {actual_count}건 (누락 {diff}건)")
                for t in missing[:3]:
                    print(f"       누락: {t[:50]}")
            elif my_count > 0:
                print(f"  ✅ {source:<18} {my_count}건 일치")
        except Exception as e:
            print(f"  ❓ {source:<18} korea.kr 검증 실패 ({str(e)[:30]})")
        time.sleep(0.3)

    # 금융기관 개별 사이트 검증
    if VERIFY_FINANCE_PLAYWRIGHT:
        for source, count_fn in FINANCE_VERIFIERS:
            my_count = collected.get(source, 0)
            try:
                actual = count_fn(s, target)
                if actual > my_count:
                    mismatches[source] = (my_count, actual)
                    print(f"  ⚠️  {source:<18} 수집 {my_count}건 / 실제 {actual}건 (누락 {actual - my_count}건)")
                elif my_count > 0:
                    print(f"  ✅ {source:<18} {my_count}건 일치")
                else:
                    print(f"  ─  {source:<18} 수집 0건 / 실제 {actual}건")
                    if actual > 0:
                        mismatches[source] = (0, actual)
            except Exception as e:
                print(f"  ❓ {source:<18} 검증 실패 ({str(e)[:30]})")
            time.sleep(0.5)
    else:
        print("  [금융기관 Playwright 검증 비활성화] VERIFY_FINANCE_PLAYWRIGHT=false")

    if not mismatches:
        print(f"\n  ✅ 모든 기관 건수 일치!")
    else:
        total_missing = sum(actual - my for my, actual in mismatches.values())
        print(f"\n  ⚠️  {len(mismatches)}개 기관에서 총 {total_missing}건 누락 감지")

    return mismatches


def fill_missing(items: list[dict], mismatches: dict, target: date) -> list[dict]:
    """누락된 기관의 보도자료를 재크롤링하여 보완"""
    if not mismatches:
        return items

    print(f"\n{'━' * 60}")
    print(f"  누락분 재크롤링 ({len(mismatches)}개 기관)")
    print(f"{'━' * 60}")

    from briefingroom.crawlers import CRAWLERS
    crawler_map = dict(CRAWLERS)

    existing_keys = {(it["title"].strip(), it["date"]) for it in items}
    added = 0

    for source, (my_count, actual) in mismatches.items():
        # korea.kr에서 해당 기관 보도자료 재수집
        s = _session()
        ds = target.isoformat()
        new_items = []

        for pg in range(1, 15):
            try:
                r = s.get(f"https://www.korea.kr/briefing/pressReleaseList.do"
                          f"?pageIndex={pg}&startDate={ds}&endDate={ds}", timeout=15)
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, "lxml")
                found = 0
                for li in soup.find_all("li"):
                    a = li.find("a", href=lambda h: h and "pressReleaseView" in h)
                    if not a:
                        continue
                    spans = li.find_all("span")
                    span_texts = [sp.get_text(strip=True) for sp in spans if sp.get_text(strip=True)]
                    dt = src = None
                    for sp in reversed(span_texts):
                        if not dt and re.match(r"^\d{4}\.\d{2}\.\d{2}$", sp):
                            dt = sp
                        elif not src and re.match(r"^[\w가-힣]{2,}$", sp) and sp != dt:
                            src = sp
                    if src != source or not dt:
                        continue
                    iso = dt.replace(".", "-")
                    if iso != ds:
                        continue

                    title = a.get_text(strip=True)
                    for cut in ["관련 보도자료", "*자세한"]:
                        idx = title.find(cut)
                        if idx > 10:
                            title = title[:idx]
                    title = re.sub(r"\d{4}\.\d{2}\.\d{2}.*$", "", title).strip().rstrip(".")

                    nid_m = re.search(r"newsId=(\d+)", a.get("href", ""))
                    if not nid_m:
                        continue
                    detail_url = f"https://www.korea.kr/briefing/pressReleaseView.do?newsId={nid_m.group(1)}"

                    key = (title.strip(), iso)
                    if key in existing_keys:
                        continue

                    # 첨부파일 수집
                    pdfs, hwps = [], []
                    try:
                        r2 = s.get(detail_url, timeout=15)
                        if r2.status_code == 200:
                            soup2 = BeautifulSoup(r2.text, "lxml")
                            for a2 in soup2.find_all("a", href=re.compile(r"/common/download\.do")):
                                href = a2["href"].replace("&amp;", "&")
                                full = "https://www.korea.kr" + href if not href.startswith("http") else href
                                fn = a2.get_text(strip=True).lower()
                                if re.search(r"\.pdf", fn):
                                    pdfs.append(full)
                                elif re.search(r"\.hwp", fn):
                                    hwps.append(full)
                                else:
                                    pdfs.append(full)
                    except Exception as e:
                        print(f"    [상세 재수집 실패] {source} | {title[:40]} | {str(e)[:40]}")

                    new_items.append({
                        "source": source, "title": title, "url": detail_url,
                        "date": iso, "pdfs": pdfs, "hwps": hwps,
                        "files": [], "text": "", "summary": "",
                    })
                    existing_keys.add(key)
                    found += 1
                if found == 0 and pg > 3:
                    break
            except Exception as e:
                print(f"  [korea.kr 재수집 중단] {source} | {str(e)[:40]}")
                break
            time.sleep(0.3)

        # 개별 크롤러로도 시도
        if len(new_items) < (actual - my_count) and source in crawler_map:
            try:
                crawler_items = crawler_map[source](target)
                for ci in crawler_items:
                    key = (ci["title"].strip(), ci["date"])
                    if key not in existing_keys:
                        new_items.append(ci)
                        existing_keys.add(key)
            except Exception as e:
                print(f"  [개별 크롤러 보완 실패] {source} | {str(e)[:40]}")

        if new_items:
            items.extend(new_items)
            added += len(new_items)
            print(f"  → {source}: +{len(new_items)}건 보완 (총 {my_count + len(new_items)}/{actual}건)")
        else:
            print(f"  → {source}: 추가 수집 실패")

    print(f"\n  보완 완료: +{added}건 추가")
    return items
