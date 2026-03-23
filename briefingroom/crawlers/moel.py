from __future__ import annotations

from .common import *

def crawl_moel(target):
    """고용노동부 — Playwright (상대경로 href 처리)"""
    print("\n[고용노동부]")
    BASE     = "https://www.moel.go.kr"
    LIST_URL = f"{BASE}/news/enews/report/enewsList.do?pageIndex=1"
    BASE_DIR = f"{BASE}/news/enews/report/"
    results  = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
                **_pw_proxy_arg())
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
            page.goto(LIST_URL, wait_until="networkidle", timeout=30000)
            soup = BeautifulSoup(page.content(), "lxml")
            seen = set()

            for row in soup.select("table tbody tr"):
                text = row.get_text(" ", strip=True)
                dm   = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                if not dm: continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date < target.isoformat(): continue
                if row_date != target.isoformat(): continue
                a = row.find("a", href=True)
                if not a: continue
                href = a["href"]
                # enewsView.do?... 형태 — 절대경로 조합
                if href.startswith("http"):
                    full_url = href
                elif href.startswith("/"):
                    full_url = BASE + href
                else:
                    full_url = BASE_DIR + href
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("고용노동부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST_URL, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
