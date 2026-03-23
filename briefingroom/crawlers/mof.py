from __future__ import annotations

from .common import *

def crawl_mof(target):
    """해양수산부 — Playwright (fn_selectDoc + jfile 다운로드)"""
    print("\n[해양수산부]")
    BASE = "https://www.mof.go.kr"
    LIST = f"{BASE}/doc/ko/selectDocList.do?menuSeq=971&bbsSeq=10&curPage=1"
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

            for row in soup.select("table tbody tr"):
                text = row.get_text(" ", strip=True)
                dm   = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                if not dm: continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date < target.isoformat(): continue
                if row_date != target.isoformat(): continue

                # 제목 링크 (fn_selectDoc)
                title_a = row.find("a", onclick=re.compile(r"fn_selectDoc"))
                if not title_a: continue
                seq_m = re.search(r"fn_selectDoc\('(\d+)'\)", title_a.get("onclick",""))
                if not seq_m: continue
                seq_id = seq_m.group(1)
                title  = clean_title(title_a.get_text(strip=True))

                detail_url = f"{BASE}/doc/ko/selectDocDetail.do?menuSeq=971&bbsSeq=10&seq={seq_id}"
                if detail_url in seen: continue
                seen.add(detail_url)

                # 파일 링크 직접 수집 (목록에서 바로)
                pdfs, hwps, seen2 = [], [], set()
                for a2 in row.find_all("a", href=re.compile(r"readDownloadFile")):
                    h2 = a2["href"]
                    full2 = BASE + h2 if not h2.startswith("http") else h2
                    if full2 in seen2: continue
                    seen2.add(full2)
                    fn = a2.get_text(strip=True).lower()
                    # 파일명에서 확장자 추출
                    if re.search(r"\.pdf", fn) or "pdf" in fn: pdfs.append(full2)
                    else: hwps.append(full2)

                # 파일이 없으면 상세 페이지에서 추가 수집
                if not pdfs and not hwps:
                    page.goto(detail_url, wait_until="networkidle", timeout=30000)
                    soup2 = BeautifulSoup(page.content(), "lxml")
                    for a2 in soup2.find_all("a", href=re.compile(r"readDownloadFile|FileDown|download", re.I)):
                        h2 = a2["href"]
                        full2 = BASE + h2 if not h2.startswith("http") else h2
                        fn = a2.get_text(strip=True).lower()
                        if re.search(r"\.pdf", fn): pdfs.append(full2)
                        else: hwps.append(full2)
                    page.goto(LIST, wait_until="networkidle", timeout=30000)
                    soup = BeautifulSoup(page.content(), "lxml")

                print(f"  ✓ {title[:60]}")
                results.append(make_item("해양수산부", title, detail_url,
                                         row_date, pdfs, hwps))
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
