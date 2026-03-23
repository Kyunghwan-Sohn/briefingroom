from __future__ import annotations

from .common import *

def crawl_msit(target):
    """과학기술정보통신부 — Playwright (div.toggle > a > div.date)"""
    print("\n[과학기술정보통신부]")
    MONTHS = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06",
               "Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}
    BASE = "https://www.msit.go.kr"
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
            page.goto(f"{BASE}/bbs/list.do?sCode=user&mPid=208&mId=307",
                      wait_until="networkidle", timeout=30000)
            soup = BeautifulSoup(page.content(), "lxml")
            today_items = []

            for div in soup.find_all("div", class_="toggle"):
                # div.toggle에서 날짜, fn_detail, 제목 직접 추출
                date_div  = div.find("div", class_="date")
                if not date_div: continue
                date_text = date_div.get_text(strip=True)
                # 날짜 형식: "2026. 3. 18" 또는 "Mar 18, 2026"
                dm = re.search(r"(\d{4})[.\s]+\s*(\d{1,2})[.\s]+\s*(\d{1,2})", date_text)
                if not dm: continue
                iso = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
                if iso < target.isoformat(): continue
                if iso != target.isoformat(): continue

                # fn_detail ID — div 전체 텍스트에서 추출
                ntt_m = re.search(r"fn_detail\((\d+)\)", str(div))
                if not ntt_m: continue

                title_el = div.find("p", class_="title")
                title = clean_title(title_el.get_text(strip=True)) if title_el else ""
                if not title: continue

                today_items.append({
                    "id": ntt_m.group(1), "date": iso, "title": title
                })

            for item in today_items:
                detail_url = (f"{BASE}/bbs/view.do?sCode=user&mPid=208"
                              f"&mId=307&nttSeqNo={item['id']}")
                page.goto(detail_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                for a2 in soup2.find_all("a"):
                    oc2 = a2.get("onclick","")
                    if "fn_download" not in oc2: continue
                    m2 = re.search(
                        r"fn_download\('(\d+)',\s*'(\d+)',\s*'([^']+)'\)", oc2)
                    if not m2: continue
                    atch_no, ord_no, ext = m2.group(1), m2.group(2), m2.group(3)
                    url = (f"{BASE}/ssm/file/fileDown.do"
                           f"?atchFileNo={atch_no}&fileOrd={ord_no}&fileBtn=A")
                    if ext.lower() == "pdf": pdfs.append(url)
                    else: hwps.append(url)
                pdfs = list(dict.fromkeys(pdfs))
                hwps = list(dict.fromkeys(hwps))
                print(f"  ✓ {item['title'][:60]}")
                results.append(make_item("과학기술정보통신부", item["title"],
                                         detail_url, item["date"], pdfs, hwps))
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results
