from __future__ import annotations

from .common import *

def crawl_mss(target):
    """중소벤처기업부 — Playwright (doBbsFView onclick → View.do)"""
    print("\n[중소벤처기업부]")
    BASE = "https://www.mss.go.kr"
    LIST = f"{BASE}/site/smba/ex/bbs/List.do?cbIdx=86&pageIndex=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
                **pw_proxy_arg())
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

            for tr in soup.select("table tbody tr"):
                onclick = tr.get("onclick", "")
                if not onclick: continue
                # doBbsFView('86','1066342','16010100','1066342')
                m = re.search(r"doBbsFView\('(\d+)','(\d+)'", onclick)
                if not m: continue
                cb_idx, bc_idx = m.group(1), m.group(2)

                text = tr.get_text(" ", strip=True)
                dm   = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                if not dm: continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date < target.isoformat(): continue
                if row_date != target.isoformat(): continue

                full_url = f"{BASE}/site/smba/ex/bbs/View.do?cbIdx={cb_idx}&bcIdx={bc_idx}"
                if full_url in seen: continue
                seen.add(full_url)

                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")

                # 제목: h4 태그
                title_el = soup2.find("h4")
                if not title_el:
                    title_el = soup2.find("h2", class_="h-tit")
                title = clean_title(title_el.get_text(strip=True)) if title_el else clean_title(text.split("담당부서")[0])

                # 파일: /common/board/Download.do
                pdfs, hwps, seen2 = [], [], set()
                for a2 in soup2.find_all("a", href=re.compile(r"Download\.do")):
                    h2 = a2["href"]
                    if h2 in seen2: continue
                    seen2.add(h2)
                    full2 = BASE + h2 if not h2.startswith("http") else h2
                    fn = a2.get_text(strip=True).lower()
                    # streFileNm에서 확장자 추출
                    ext_m = re.search(r"streFileNm=([^&]+)", h2)
                    ext = ext_m.group(1)[-3:].lower() if ext_m else ""
                    if ext == "pdf" or "pdf" in fn: pdfs.append(full2)
                    else: hwps.append(full2)

                print(f"  ✓ {title[:60]}")
                results.append(make_item("중소벤처기업부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
