"""금융 유관기관 크롤러 (requests 전용, IP 차단 방지)

korea.kr에 올라오지 않는 금융기관 보도자료를 개별 수집.
TLS 어댑터 + 세션 재사용 + 딜레이로 차단 방지.
"""
from __future__ import annotations

import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

from briefingroom.crawlers.koreakr import _new_session, _clean_title

DELAY = 1.0


def _make_item(source, title, url, date_str, pdfs=None, hwps=None):
    return {
        "source": source, "title": title, "url": url,
        "date": date_str,
        "pdfs": pdfs or [], "hwps": hwps or [],
        "files": [], "text": "", "summary": "",
    }


# ═══════════════════════════════════════════════════════════
# 1. 금융감독원 (requests 직접 파싱)
# ═══════════════════════════════════════════════════════════
def crawl_fss(target: date) -> list[dict]:
    print(f"\n  [금융감독원] {target}")
    s = _new_session()
    BASE = "https://www.fss.or.kr"
    results = []
    target_str = target.isoformat()

    for pg in range(1, 5):
        url = f"{BASE}/fss/bbs/B0000188/list.do?menuNo=200218&pageIndex={pg}"
        try:
            r = s.get(url, timeout=15)
            if r.status_code != 200:
                break
        except Exception as e:
            print(f"    [오류] {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        found = older = 0

        for row in soup.select("table tbody tr"):
            text = row.get_text(" ", strip=True)
            dm = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
            if not dm:
                continue
            row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            if row_date < target_str:
                older += 1
                if older >= 3:
                    return results
                continue
            if row_date != target_str:
                continue

            a = row.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            full = BASE + href if not href.startswith("http") else href
            title = _clean_title(a.get_text(strip=True))

            # 상세 페이지에서 첨부파일 수집
            time.sleep(DELAY)
            pdfs, hwps = _fetch_fss_files(s, full, BASE)

            print(f"    ✓ {title[:55]}")
            results.append(_make_item("금융감독원", title, full, row_date, pdfs, hwps))
            found += 1

        if found == 0 and pg > 1:
            break
        time.sleep(DELAY)

    return results


def _fetch_fss_files(session, url, base):
    pdfs, hwps, seen = [], [], set()
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return pdfs, hwps
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            fn = a.get_text(strip=True).lower()
            if not re.search(r"download|getFile|fileDown|attach", href, re.I):
                continue
            full = base + href if not href.startswith("http") else href
            if full in seen:
                continue
            seen.add(full)
            if re.search(r"\.pdf", fn):
                pdfs.append(full)
            elif re.search(r"\.hwp", fn):
                hwps.append(full)
            else:
                pdfs.append(full)
    except Exception:
        pass
    return pdfs, hwps


# ═══════════════════════════════════════════════════════════
# 2. 한국은행 (AJAX JSON)
# ═══════════════════════════════════════════════════════════
def crawl_bok(target: date) -> list[dict]:
    print(f"\n  [한국은행] {target}")
    s = _new_session()
    BASE = "https://www.bok.or.kr"
    results = []
    target_str = target.isoformat()
    target_dot = target.strftime("%Y.%m.%d")

    url = (f"{BASE}/portal/singl/newsData/list.do"
           f"?menuNo=201263&pageIndex=1&pageUnit=20"
           f"&searchCnd=1&searchKwd=&sort=1"
           f"&sdate={target.strftime('%Y%m%d')}&edate={target.strftime('%Y%m%d')}")

    try:
        r = s.get(url, timeout=15)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code}")
            return results
    except Exception as e:
        print(f"    [오류] {e}")
        return results

    soup = BeautifulSoup(r.text, "lxml")

    # a.title 패턴 (기존 크롤러에서 확인됨)
    for a in soup.find_all("a", class_="title"):
        href = a.get("href", "")
        title = _clean_title(a.get_text(strip=True))
        if not title:
            continue

        # 부모에서 날짜 찾기
        parent = a.find_parent()
        date_span = None
        for _ in range(4):
            if not parent:
                break
            date_span = parent.find("span", class_="date")
            if date_span:
                break
            parent = parent.find_parent()

        if not date_span:
            continue
        date_text = re.sub(r"등록일", "", date_span.get_text(strip=True))
        dm = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", date_text)
        if not dm:
            continue
        row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
        if row_date != target_str:
            continue

        full_url = BASE + href if not href.startswith("http") else href

        # 상세 페이지에서 파일 수집
        time.sleep(DELAY)
        pdfs, hwps = _fetch_bok_files(s, full_url, BASE)

        print(f"    ✓ {title[:55]}")
        results.append(_make_item("한국은행", title, full_url, row_date, pdfs, hwps))

    return results


def _fetch_bok_files(session, url, base):
    pdfs, hwps, seen = [], [], set()
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return pdfs, hwps
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=re.compile(r"/fileSrc/")):
            h = a["href"]
            fn = a.get_text(strip=True).lower()
            if "뷰어" in fn or "viewer" in fn:
                continue
            full = base + h if not h.startswith("http") else h
            if full in seen:
                continue
            seen.add(full)
            if re.search(r"\.pdf", fn):
                pdfs.append(full)
            elif re.search(r"\.hwp", fn):
                hwps.append(full)
    except Exception:
        pass
    return pdfs, hwps


# ═══════════════════════════════════════════════════════════
# 3. 한국거래소 (KRX Open API)
# ═══════════════════════════════════════════════════════════
def crawl_krx(target: date) -> list[dict]:
    print(f"\n  [한국거래소] {target}")
    s = _new_session()
    BASE = "https://open.krx.co.kr"
    results = []
    target_str = target.isoformat()
    target_dot = target.strftime("%Y.%m.%d")

    # KRX 보도자료 목록 페이지
    url = f"{BASE}/contents/OPN/05/05000000/OPN05000000.jsp"
    try:
        r = s.get(url, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "05010000" not in href and "boardSeq" not in href:
                continue
            text = a.get_text(strip=True)
            # 날짜 찾기
            parent = a.find_parent("li") or a.find_parent("tr") or a.find_parent("div")
            if not parent:
                continue
            ptext = parent.get_text(" ", strip=True)
            dm = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", ptext)
            if not dm:
                continue
            row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            if row_date != target_str:
                continue

            full = BASE + href if not href.startswith("http") else href
            title = _clean_title(text)
            if not title or len(title) < 5:
                continue

            print(f"    ✓ {title[:55]}")
            results.append(_make_item("한국거래소", title, full, row_date))
    except Exception as e:
        print(f"    [오류] {e}")

    return results


# ═══════════════════════════════════════════════════════════
# 4. 예금보험공사
# ═══════════════════════════════════════════════════════════
def crawl_kdic(target: date) -> list[dict]:
    print(f"\n  [예금보험공사] {target}")
    s = _new_session()
    BASE = "https://www.kdic.or.kr"
    results = []
    target_str = target.isoformat()

    # 보도자료 검색 API 시도
    for endpoint in [
        f"{BASE}/news/press_list.do",
        f"{BASE}/cms/bbs/press/list.do",
        f"{BASE}/bbs/press/list.do",
    ]:
        try:
            r = s.get(endpoint, timeout=10)
            if r.status_code == 200 and len(r.text) > 3000:
                soup = BeautifulSoup(r.text, "lxml")
                for row in soup.select("table tbody tr"):
                    text = row.get_text(" ", strip=True)
                    dm = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                    if not dm:
                        continue
                    row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                    if row_date != target_str:
                        continue
                    a = row.find("a", href=True)
                    if not a:
                        continue
                    title = _clean_title(a.get_text(strip=True))
                    href = a["href"]
                    full = BASE + href if not href.startswith("http") else href
                    print(f"    ✓ {title[:55]}")
                    results.append(_make_item("예금보험공사", title, full, row_date))
                if results:
                    return results
        except Exception:
            continue

    if not results:
        print("    (보도자료 페이지 접근 실패 — JS 렌더링 필요)")
    return results


# ═══════════════════════════════════════════════════════════
# 5. 금융결제원
# ═══════════════════════════════════════════════════════════
def crawl_kftc(target: date) -> list[dict]:
    print(f"\n  [금융결제원] {target}")
    s = _new_session()
    BASE = "https://www.kftc.or.kr"
    results = []
    target_str = target.isoformat()

    url = f"{BASE}/kftc/data/EgovBbsList.do?bbsId=BBSMSTR_000000000016&pageIndex=1"
    try:
        r = s.get(url, timeout=10)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code}")
            return results
        soup = BeautifulSoup(r.text, "lxml")
        for row in soup.select("table tbody tr"):
            text = row.get_text(" ", strip=True)
            dm = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
            if not dm:
                continue
            row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            if row_date != target_str:
                continue
            a = row.find("a", href=True)
            if not a:
                continue
            title = _clean_title(a.get_text(strip=True))
            href = a["href"]
            full = BASE + href if not href.startswith("http") else href
            print(f"    ✓ {title[:55]}")
            results.append(_make_item("금융결제원", title, full, row_date))
    except Exception as e:
        print(f"    [오류] {e}")

    return results


# ═══════════════════════════════════════════════════════════
# 6. 금융보안원
# ═══════════════════════════════════════════════════════════
def crawl_fsec(target: date) -> list[dict]:
    print(f"\n  [금융보안원] {target}")
    s = _new_session()
    BASE = "https://www.fsec.or.kr"
    results = []
    target_str = target.isoformat()

    url = f"{BASE}/bbs/2"
    try:
        r = s.get(url, timeout=10)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code}")
            return results
        soup = BeautifulSoup(r.text, "lxml")
        for row in soup.select("table tbody tr"):
            text = row.get_text(" ", strip=True)
            dm = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
            if not dm:
                continue
            row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            if row_date != target_str:
                continue
            a = row.find("a", href=True)
            if not a:
                continue
            title = _clean_title(a.get_text(strip=True))
            href = a["href"]
            full = BASE + href if not href.startswith("http") else href
            print(f"    ✓ {title[:55]}")
            results.append(_make_item("금융보안원", title, full, row_date))
    except Exception as e:
        print(f"    [오류] {e}")

    return results


# ═══════════════════════════════════════════════════════════
# 7. 한국은행 (Playwright)
# ═══════════════════════════════════════════════════════════
def crawl_bok_pw(target: date) -> list[dict]:
    print(f"\n  [한국은행] {target}")
    from playwright.sync_api import sync_playwright

    BASE = "https://www.bok.or.kr"
    results = []
    target_str = target.isoformat()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="ko-KR", timezone_id="Asia/Seoul",
            )
            page = ctx.new_page()
            page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            page.goto(f"{BASE}/portal/singl/newsData/list.do?menuNo=201263", wait_until="networkidle", timeout=25000)
            soup = BeautifulSoup(page.content(), "lxml")

            for a in soup.find_all("a", class_="title"):
                href = a.get("href", "")
                title = _clean_title(a.get_text(strip=True))
                if not title:
                    continue

                # 부모에서 날짜 찾기
                parent = a
                date_span = None
                for _ in range(5):
                    parent = parent.find_parent()
                    if not parent:
                        break
                    date_span = parent.find("span", class_="date")
                    if date_span:
                        break
                if not date_span:
                    continue
                date_text = re.sub(r"등록일", "", date_span.get_text(strip=True))
                dm = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", date_text)
                if not dm:
                    continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date != target_str:
                    continue

                full_url = BASE + href if not href.startswith("http") else href

                # 상세 페이지에서 파일 수집
                page.goto(full_url, wait_until="networkidle", timeout=25000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps, seen = [], [], set()
                for a2 in soup2.find_all("a", href=re.compile(r"/fileSrc/")):
                    h = a2["href"]
                    fn = a2.get_text(strip=True).lower()
                    if "뷰어" in fn or "viewer" in fn:
                        continue
                    full2 = BASE + h if not h.startswith("http") else h
                    if full2 in seen:
                        continue
                    seen.add(full2)
                    if re.search(r"\.pdf", fn):
                        pdfs.append(full2)
                    elif re.search(r"\.hwp", fn):
                        hwps.append(full2)

                print(f"    ✓ {title[:55]}")
                results.append(_make_item("한국은행", title, full_url, row_date, pdfs, hwps))

            browser.close()
    except Exception as e:
        print(f"    [Playwright 오류] {e}")

    return results


# ═══════════════════════════════════════════════════════════
# 8. 한국거래소 (Playwright)
# ═══════════════════════════════════════════════════════════
def crawl_krx_pw(target: date) -> list[dict]:
    print(f"\n  [한국거래소] {target}")
    from playwright.sync_api import sync_playwright

    BASE = "https://open.krx.co.kr"
    results = []
    target_str = target.isoformat()
    seen = set()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="ko-KR", timezone_id="Asia/Seoul",
            )
            page = ctx.new_page()
            page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            page.goto(f"{BASE}/contents/OPN/05/05000000/OPN05000000.jsp", wait_until="networkidle", timeout=25000)
            soup = BeautifulSoup(page.content(), "lxml")

            # li 또는 div에서 날짜+제목 추출
            for el in soup.find_all(["li", "div"]):
                text = el.get_text(" ", strip=True)
                dm = re.search(r"(\d{4})[/.\-](\d{2})[/.\-](\d{2})", text)
                if not dm:
                    continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date != target_str:
                    continue

                a = el.find("a")
                if not a:
                    continue
                title = _clean_title(a.get_text(strip=True))
                if not title or len(title) < 5 or title in seen:
                    continue
                seen.add(title)

                # KRX 보도자료는 첨부파일 없이 원문 링크만
                onclick = a.get("onclick", "")
                href = a.get("href", "#")
                # onclick에서 상세 URL 추출 시도
                seq_m = re.search(r"'(\d+)'", onclick)
                if seq_m:
                    detail_url = f"{BASE}/contents/OPN/05/05010000/OPN05010000.jsp?boardSeq={seq_m.group(1)}"
                else:
                    detail_url = BASE + href if href != "#" and not href.startswith("http") else f"{BASE}/contents/OPN/05/05000000/OPN05000000.jsp"

                print(f"    ✓ {title[:55]}")
                results.append(_make_item("한국거래소", title, detail_url, row_date))

            browser.close()
    except Exception as e:
        print(f"    [Playwright 오류] {e}")

    return results


# ═══════════════════════════════════════════════════════════
# 통합 크롤링 함수
# ═══════════════════════════════════════════════════════════

FINANCE_CRAWLERS = [
    ("금융감독원",   crawl_fss),
    ("한국은행",     crawl_bok_pw),
    ("한국거래소",   crawl_krx_pw),
    ("금융결제원",   crawl_kftc),
    ("금융보안원",   crawl_fsec),
]


def crawl_finance_all(target: date) -> list[dict]:
    """금융 유관기관 전체 크롤링"""
    print(f"\n{'─' * 50}")
    print(f"[금융 유관기관] {target} 보도자료 수집")
    print(f"{'─' * 50}")

    all_items = []
    for name, crawler in FINANCE_CRAWLERS:
        try:
            items = crawler(target)
            all_items.extend(items)
        except Exception as e:
            print(f"  [{name}] 실패: {str(e)[:60]}")
        time.sleep(DELAY * 2)

    print(f"\n  → 금융 유관기관 총 {len(all_items)}건 수집 완료")
    return all_items
