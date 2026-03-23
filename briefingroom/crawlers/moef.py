from __future__ import annotations

from .common import *

def crawl_moef(target):
    """기획재정부 — Playwright (fn_egov_select + detailNesDtaView)"""
    print("\n[기획재정부]")
    BASE = "https://mofe.go.kr"
    LIST = f"{BASE}/nw/nes/nesdta.do?bbsId=MOSFBBS_000000000028&menuNo=4010100"
    results = []
    target_str = target.strftime("%Y.%m.%d.")
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
            page.goto(LIST, wait_until="networkidle", timeout=30000)
            soup = BeautifulSoup(page.content(), "lxml")
            seen = set()

            for li in soup.find_all("li"):
                date_span = li.find("span", class_="date")
                if not date_span: continue
                if date_span.get_text(strip=True) != target_str: continue
                a = li.find("a", href=re.compile(r"fn_egov_select"))
                if not a: continue
                ntt_m = re.search(r"fn_egov_select\('([^']+)'\)", a["href"])
                if not ntt_m: continue
                ntt_id = ntt_m.group(1)
                if ntt_id in seen: continue
                seen.add(ntt_id)
                title = clean_title(a.get_text(strip=True))

                # detailNesDtaView URL 직접 구성
                detail_url = (f"{BASE}/nw/nes/detailNesDtaView.do"
                              f"?searchBbsId1=MOSFBBS_000000000028"
                              f"&searchNttId1={ntt_id}&menuNo=4010100")
                page.goto(detail_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")

                # FileDown 패턴에서 파일명으로 pdf/hwp 판별, 중복 제거
                pdfs, hwps, seen2 = [], [], set()
                for a2 in soup2.find_all("a", href=re.compile(r"FileDown\.do")):
                    href2 = a2["href"]
                    if href2 in seen2: continue
                    fn = a2.get_text(strip=True).lower()
                    # '다운로드' 텍스트만 있는 링크는 스킵
                    if not re.search(r"\.(hwp|pdf)", fn): continue
                    seen2.add(href2)
                    full2 = BASE + href2 if not href2.startswith("http") else href2
                    if ".pdf" in fn: pdfs.append(full2)
                    else: hwps.append(full2)

                print(f"  ✓ {title[:60]}")
                results.append(make_item("기획재정부", title, detail_url,
                                         target.isoformat(), pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")

            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
