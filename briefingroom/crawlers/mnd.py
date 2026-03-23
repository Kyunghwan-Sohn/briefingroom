from __future__ import annotations

from .common import *

def crawl_mnd(target):
    """국방부 — Playwright (jf_view)"""
    print("\n[국방부]")
    BASE     = "https://www.mnd.go.kr"
    LIST_URL = (f"{BASE}/user/newsInUserRecord.action"
                f"?siteId=mnd&handle=I_669&id=mnd_020500000000")
    results  = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
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
            page.goto(LIST_URL, wait_until="networkidle", timeout=30000)
            soup = BeautifulSoup(page.content(), "lxml")
            today_items = []
            for li in soup.find_all("li"):
                html_li = li.decode_contents()
                if "jf_view" not in html_li: continue
                dm = re.search(r"작성일\s*:\s*(\d{4}-\d{2}-\d{2})", li.get_text())
                a  = li.find("a", attrs={"onclick": re.compile(r"jf_view")})
                if not (dm and a): continue
                if dm.group(1) != target.isoformat(): continue
                seq_m = re.search(r"jf_view\('([^']+)'\)", a.get("onclick",""))
                if not seq_m: continue
                today_items.append({
                    "seq": seq_m.group(1), "date": dm.group(1),
                    "title": clean_title(a.get_text(strip=True))
                })
            for item in today_items:
                detail_url = (f"{BASE}/user/newsInUserRecord.action"
                              f"?siteId=mnd&newsId=I_669&newsSeq={item['seq']}"
                              f"&page=1&command=view&id=mnd_020500000000")
                page.goto(detail_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                print(f"  ✓ {item['title'][:60]}")
                results.append(make_item("국방부", item["title"],
                                         detail_url, item["date"], pdfs, hwps))
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
