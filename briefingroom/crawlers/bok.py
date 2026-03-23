from __future__ import annotations

from .common import *

def crawl_bok(target):
    """한국은행 — Playwright (a.title + span.date + /fileSrc/ 다운로드)"""
    print("\n[한국은행]")
    BASE = "https://www.bok.or.kr"
    LIST = f"{BASE}/portal/singl/newsData/list.do?menuNo=201263"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"),
                locale="ko-KR", timezone_id="Asia/Seoul",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            page.goto(LIST, wait_until="networkidle", timeout=30000)
            soup = BeautifulSoup(page.content(), "lxml")
            seen = set()

            for a in soup.find_all("a", class_="title"):
                href = a["href"]
                title = clean_title(a.get_text(strip=True))
                # 날짜: 부모에서 span.date 찾기
                parent = a.find_parent()
                date_span = None
                for _ in range(4):
                    if not parent: break
                    date_span = parent.find("span", class_="date")
                    if date_span: break
                    parent = parent.find_parent()
                if not date_span: continue
                date_text = re.sub(r"등록일", "", date_span.get_text(strip=True))
                dm = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", date_text)
                if not dm: continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date < target.isoformat(): continue
                if row_date != target.isoformat(): continue

                full_url = BASE + href if not href.startswith("http") else href
                if full_url in seen: continue
                seen.add(full_url)

                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")

                # 파일: /fileSrc/ 패턴
                pdfs, hwps, seen2 = [], [], set()
                for a2 in soup2.find_all("a", href=re.compile(r"/fileSrc/")):
                    h2 = a2["href"]
                    fn = a2.get_text(strip=True).lower()
                    if "뷰어" in fn or "viewer" in fn.lower(): continue
                    full2 = BASE + h2 if not h2.startswith("http") else h2
                    if full2 in seen2: continue
                    seen2.add(full2)
                    if re.search(r"\.pdf", fn): pdfs.append(full2)
                    elif re.search(r"\.hwp", fn): hwps.append(full2)

                print(f"  ✓ {title[:60]}")
                results.append(make_item("한국은행", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")

            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
