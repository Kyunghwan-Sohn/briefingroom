from __future__ import annotations

from .common import *

def crawl_motie(target):
    """산업통상자원부 — Playwright (목록에서 직접 파일 수집, 상세 페이지 접근 없음)"""
    print("\n[산업통상자원부]")
    BASE = "https://www.motie.go.kr"
    LIST = f"{BASE}/kor/article/ATCL3f49a5a8c?pageIndex=1"
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

                # onclick에서 seq ID 추출
                seq_m = None
                for el in row.find_all(attrs={"onclick": True}):
                    seq_m = re.search(r"article\.view\('(\d+)'\)", el.get("onclick",""))
                    if seq_m: break
                if not seq_m: continue
                seq_id   = seq_m.group(1)
                detail_url = f"{BASE}/kor/article/ATCL3f49a5a8c/{seq_id}/view"
                if detail_url in seen: continue
                seen.add(detail_url)

                # 제목
                title_a = row.find("a", href="#")
                title = clean_title(title_a.get_text(strip=True)) if title_a else clean_title(text[:60])

                # 파일: 목록에서 /attach/down/ 패턴 직접 수집
                pdfs, hwps, seen2 = [], [], set()
                for a2 in row.find_all("a", href=re.compile(r"/attach/down/")):
                    h2   = a2["href"]
                    full = BASE + h2 if not h2.startswith("http") else h2
                    if full in seen2: continue
                    seen2.add(full)
                    fn = a2.get_text(strip=True).lower()
                    if re.search(r"\.hwp", fn) or re.search(r"\.hwp", full, re.I):
                        hwps.append(full)
                    else:
                        pdfs.append(full)

                print(f"  ✓ {title[:60]}")
                results.append(make_item("산업통상자원부", title, detail_url,
                                         row_date, pdfs, hwps))
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
