from __future__ import annotations

from .common import *

def crawl_fsc(target):
    """금융위원회 — Playwright
    등록일이 배포일보다 하루 늦으므로 target ~ target+1일 범위로 수집.
    제목에 날짜 패턴('YY.M.D) 있으면 우선 사용.
    """
    print("\n[금융위원회]")
    from datetime import timedelta
    BASE = "https://www.fsc.go.kr"
    results = []
    # 허용 날짜 범위: target 당일 + 다음날 (등록 지연 고려)
    allowed = {target.isoformat(),
               (target + timedelta(days=1)).isoformat()}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
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
            page.goto(f"{BASE}/no010101", wait_until="networkidle", timeout=30000)
            soup = BeautifulSoup(page.content(), "lxml")

            links = []
            seen  = set()
            for a in soup.find_all("a", href=re.compile(r"/no010101/\d+")):
                href = a["href"].split("?")[0]
                if href in seen: continue
                seen.add(href)
                title = clean_title(re.sub(r"\s+", " ", a.get_text(strip=True)))
                links.append((BASE + href, title))

            older = 0
            for full_url, title in links:
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")

                # span에서 등록일 추출
                row_date = None
                for span in soup2.find_all("span"):
                    t = span.get_text(strip=True)
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", t):
                        row_date = t
                        break

                if not row_date: continue

                # 허용 범위 밖이면 스킵/종료
                if row_date < target.isoformat():
                    older += 1
                    if older >= 3: break
                    continue
                if row_date not in allowed:
                    continue

                older = 0
                pdfs, hwps = extract_file_links(soup2, BASE)
                print(f"  ✓ {title[:60]}")
                results.append(make_item("금융위원회", title, full_url,
                                         target.isoformat(), pdfs, hwps))

            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
