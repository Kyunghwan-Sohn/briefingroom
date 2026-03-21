from __future__ import annotations

from .common import *

def crawl_mofa(target):
    """외교부 — Playwright (SSL 우회)"""
    print("\n[외교부]")
    BASE = "https://www.mofa.go.kr"
    LIST = f"{BASE}/www/brd/m_4080/list.do?page=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--ignore-certificate-errors", "--disable-web-security"])
            page = browser.new_page(ignore_https_errors=True)
            page.set_extra_http_headers(HEADERS)
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
                href = a["href"]
                if href.startswith("./"): href = "/www/brd/m_4080/" + href[2:]
                full = BASE + href if not href.startswith("http") else href
                if full in seen: continue
                seen.add(full)
                page.goto(full, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("외교부", title, full, row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
