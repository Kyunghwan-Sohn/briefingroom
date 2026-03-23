from __future__ import annotations

from .common import *

def crawl_mogef(target):
    """성평등가족부 — Playwright (메인 방문 후 fn_selectView)"""
    print("\n[성평등가족부]")
    BASE = "https://www.mogef.go.kr"
    LIST = f"{BASE}/nw/rpd/nw_rpd_s001.do?mid=news405&page=1"
    results = []
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
            page.goto(BASE, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(1000)
            page.goto(LIST, wait_until="networkidle", timeout=30000)
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
                onclick = a.get("onclick", "") or a.get("href", "")
                seq_m   = re.search(r"fn_selectView\('(\d+)'\)", onclick)
                if not seq_m: continue
                full_url = f"{BASE}/nw/rpd/nw_rpd_s001d.do?mid=news405&bbtSn={seq_m.group(1)}"
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("성평등가족부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
