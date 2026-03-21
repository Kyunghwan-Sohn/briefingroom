from __future__ import annotations

from .common import *

def crawl_moe(target):
    """교육부 — Playwright (newsBox 카드형, h3 제목, fileDown 파일)"""
    print("\n[교육부]")
    BASE = "https://www.moe.go.kr"
    LIST = f"{BASE}/boardCnts/list.do?boardID=294&m=020402&s=moe&page=1"
    results = []
    target_str = target.strftime("%Y-%m-%d")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
                locale="ko-KR", timezone_id="Asia/Seoul",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            page.goto(LIST, wait_until="networkidle", timeout=30000)
            soup = BeautifulSoup(page.content(), "lxml")
            seen = set()

            for a in soup.find_all("a", class_="newsBox"):
                date_p = a.find("p", class_="date")
                if not date_p: continue
                row_date = date_p.get_text(strip=True)
                if row_date < target_str: continue
                if row_date != target_str: continue
                href = a.get("href", "")
                if not href or href in seen: continue
                seen.add(href)
                full_url = BASE + href if not href.startswith("http") else href

                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")

                # 제목: h3 태그
                h3 = soup2.find("h3")
                title = clean_title(h3.get_text(strip=True)) if h3 else "제목없음"

                # 파일: /boardCnts/fileDown.do?...&fileSeq=... 패턴
                pdfs, hwps, seen2 = [], [], set()
                for a2 in soup2.find_all("a", href=re.compile(r"fileDown\.do")):
                    h2 = a2["href"]
                    if h2 in seen2: continue
                    seen2.add(h2)
                    full2 = BASE + h2 if not h2.startswith("http") else h2
                    fn = a2.get_text(strip=True).lower()
                    # 파일명 없으면 URL에서 판별 불가 → 헤드 요청으로 Content-Type 확인
                    # 일단 hwp로 저장 (다운로드 시 확장자 판별)
                    hwps.append(full2)

                print(f"  ✓ {title[:60]}")
                results.append(make_item("교육부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")

            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
