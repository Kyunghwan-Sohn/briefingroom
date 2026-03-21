from __future__ import annotations

from .common import *

def crawl_unikorea(target):
    """통일부 — requests"""
    print("\n[통일부]")
    s   = new_session()
    BASE = "https://www.unikorea.go.kr"
    results = []
    for pg in range(1, 4):
        url  = f"{BASE}/web/unikorea/bbs/bbs_0000000000000004/list?cp={pg}"
        soup = get_soup(url, s)
        if not soup: break
        found = older = 0
        for row in soup.select("table tbody tr"):
            text = row.get_text(" ", strip=True)
            dm   = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
            if not dm: continue
            row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            if row_date < target.isoformat():
                older += 1
                if older >= 3: return results
                continue
            if row_date != target.isoformat(): continue
            a = row.find("a", href=True)
            if not a: continue
            href = BASE + a["href"] if not a["href"].startswith("http") else a["href"]
            time.sleep(DELAY)
            soup2 = get_soup(href, new_session())
            pdfs, hwps = (extract_file_links(soup2, BASE) if soup2 else ([], []))
            title = clean_title(a.get_text(strip=True))
            print(f"  ✓ {title[:60]}")
            results.append(make_item("통일부", title, href, row_date, pdfs, hwps))
            found += 1
        if found == 0 and pg > 1: break
    return results
