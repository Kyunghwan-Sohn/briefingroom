"""
briefing.py — 대한민국 정부 26개 부처 보도자료 수집기

플로우:
  1. 각 부처 보도자료 링크 수집 (requests or Playwright)
  2. PDF 우선 다운로드, 없으면 HWP/HWPX
  3. 텍스트 추출 → .txt 저장
  4. LLM 요약

실행: python briefing.py            # 오늘
      python briefing.py 2026-03-18 # 특정 날짜
"""
import re
import sys
import time
import zlib
import zipfile
from datetime import date
from pathlib import Path

import olefile
import pdfplumber
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ── 설정 ──────────────────────────────────────────────
API_KEY  = "sk-abcd-48263410568dc65eac7c5f7290d6de506187af0a6aa1ad34"
API_URL  = "https://abcllm-api.brut.bot/v1/chat/completions"
MODEL    = "[MLX] Qwen3-4B"
MAX_TEXT = 6000
TIMEOUT  = 20
DELAY    = 1.5

# GitHub Actions 환경 자동 감지
import os
if os.environ.get("GITHUB_ACTIONS"):
    BASE_DIR = Path(__file__).parent
else:
    BASE_DIR = Path.home() / "Desktop" / "briefing"
PDF_DIR  = BASE_DIR / "pdfs"
TXT_DIR  = BASE_DIR / "texts"
PDF_DIR.mkdir(exist_ok=True)
TXT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

SYSTEM_PROMPT = """당신은 대한민국 정부 정책 전문 분석가입니다.
보도자료 원문을 받으면 반드시 아래 형식으로만 답하세요.

요약: (3문장. 핵심 정책 내용 / 주요 수치·시행 시점 / 대상·효과 순서로)
키워드: 키워드1, 키워드2, 키워드3, 키워드4, 키워드5"""


# ════════════════════════════════════════════════════
# 공통 유틸
# ════════════════════════════════════════════════════

def make_item(source, title, url, date_str, pdfs, hwps):
    return {
        "source": source, "title": title, "url": url,
        "date": date_str,
        "pdfs": list(dict.fromkeys(pdfs)),
        "hwps": list(dict.fromkeys(hwps)),
        "files": [], "text": "", "summary": "",
    }

def new_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def get_soup(url, session, retries=2):
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [오류] {e}")
    return None

def clean_title(t):
    t = re.sub(r"금일\s*등록된.*$", "", t).strip()
    t = re.sub(r"^새글\s*", "", t).strip()
    t = re.sub(r"^N\s*", "", t).strip()
    return t.rstrip(". ").strip()

def extract_file_links(soup, base):
    """BeautifulSoup에서 PDF/HWP 링크 추출"""
    pdfs, hwps, seen = [], [], set()
    for a in soup.find_all("a"):
        href    = a.get("href", "")
        onclick = a.get("onclick", "")
        fname   = a.get_text(strip=True).lower()

        # onclick: location.href='/attach/down/...'
        if "location.href=" in onclick:
            m = re.search(r"location\.href='([^']+)'", onclick)
            if m: href = m.group(1)

        # fn_egov_downFile('FILE_ID','순번','확장자') — 개인정보보호위원회 등
        elif "fn_egov_downFile" in onclick:
            m = re.search(r"fn_egov_downFile\('([^']+)','(\d+)','([^']+)'\)", onclick)
            if m:
                file_id, file_sn, ext = m.group(1), m.group(2), m.group(3)
                href = f"/np/cmm/fms/FileDown.do?atchFileId={file_id}&fileSn={file_sn}&fileExtsn={ext}"
                full = base + href
                if full not in seen:
                    seen.add(full)
                    if ext.lower() == "pdf": pdfs.append(full)
                    else: hwps.append(full)
                continue

        # fn_fileDownload('atfileSn','atfileSeq') — 성평등가족부
        elif "fn_fileDownload" in onclick:
            m = re.search(r"fn_fileDownload\('(\d+)','(\d+)'\)", onclick)
            if m:
                sn, seq = m.group(1), m.group(2)
                full = base + f"/news/down.do?mid=news405&atfileSn={sn}&atfileSeq={seq}"
                fn_text = a.get_text(strip=True).lower()
                if full not in seen:
                    seen.add(full)
                    if re.search(r"\.pdf", fn_text): pdfs.append(full)
                    else: hwps.append(full)
                continue

        # openFileViewer('board_id','path/to/file.pdf','hash') — 통일부
        elif "openFileViewer" in href:
            m = re.search(r"openFileViewer\('[^']+',\s*'([^']+)'", href)
            if m:
                file_path = m.group(1)
                full = base + "/" + file_path.lstrip("/")
                if full not in seen:
                    seen.add(full)
                    if re.search(r"\.pdf", file_path, re.I): pdfs.append(full)
                    elif re.search(r"\.hwp", file_path, re.I): hwps.append(full)
            continue

        # javascript:Jnit_boardDownload('/board/file/...')
        elif re.search(r"boardDownload|fileDown", onclick, re.I):
            m = re.search(r"'(/[^']+)'", onclick)
            if m: href = m.group(1)

        if not href or href in ("#", "javascript:;", "javascript:void(0)"): continue

        # 문체부 attachFiles viewer
        if "attachFiles/viewer" in href:
            fn_m = re.search(r"fn=([^&]+)", href)
            if fn_m:
                fn_path = fn_m.group(1)
                if fn_path.startswith("http"):
                    real = fn_path
                elif fn_path.startswith("/"):
                    real = base + fn_path
                else:
                    real = base + "/attachFiles/" + fn_path
                if real not in seen:
                    seen.add(real)
                    if re.search(r"\.pdf", fn_path, re.I): pdfs.append(real)
                    elif re.search(r"\.hwp", fn_path, re.I): hwps.append(real)
            continue

        # ./ 상대경로 처리
        if href.startswith("./"):
            href = "/" + href[2:]
        full = href if href.startswith("http") else base + href
        if full in seen: continue

        is_file = re.search(
            r"(getFile|fileDown|FileDown|attach/down|/board/file/|boardDownload"
            r"|boardDownload\.es|downloadFile|downloadBbsFile|srvcId|fileOrd|\.pdf|\.hwp)", full, re.I)
        if not is_file: continue
        seen.add(full)

        if re.search(r"\.pdf", fname) or re.search(r"\.pdf", full, re.I) or re.search(r"file_ext=pd", full, re.I):
            pdfs.append(full)
        elif re.search(r"\.hwp", fname) or re.search(r"\.hwp", full, re.I) or re.search(r"file_ext=hw", full, re.I):
            hwps.append(full)
        elif re.search(r"attach/down|boardDownload|/board/file/|downloadFile", full, re.I):
            # 확장자 불명 — Content-Disposition으로 다운로드 시 판별
            if "pdf" in fname: pdfs.append(full)
            else: hwps.append(full)

    return pdfs, hwps


# ════════════════════════════════════════════════════
# Playwright 공통 크롤러
# ════════════════════════════════════════════════════

def pw_crawl_list(name, list_url, base, target,
                  row_sel="table tbody tr", date_re=None, skip_main=False):
    """
    Playwright 기반 범용 목록 크롤러 (stealth 모드).
    날짜가 target과 일치하는 행을 찾아 상세 페이지 파일 링크 수집.
    """
    results = []
    date_pat = date_re or re.compile(r"(\d{4})[.\-](\d{2})[.\-](\d{2})")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
                locale="ko-KR",
                timezone_id="Asia/Seoul",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            # 메인 도메인 먼저 방문 (쿠키/세션 확보, skip_main=True면 생략)
            if not skip_main:
                try:
                    page.goto(base, timeout=15000)
                    page.wait_for_timeout(500)
                except:
                    pass
            page.goto(list_url, wait_until="networkidle", timeout=30000)
            soup = BeautifulSoup(page.content(), "lxml")
            seen = set()

            for row in soup.select(row_sel):
                text = row.get_text(" ", strip=True)
                dm   = date_pat.search(text)
                if not dm: continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date < target.isoformat(): continue
                if row_date != target.isoformat(): continue

                a = row.find("a", href=True)
                if not a: continue
                href = re.sub(r";jsessionid=[^?&]*", "", a["href"])
                if not href.startswith("http"):
                    if href.startswith("./"):
                        href = "/" + href[2:]
                    if not href.startswith("/"):
                        href = "/" + href
                    href = base + href
                if href in seen: continue
                seen.add(href)

                page.goto(href, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, base)

                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item(name, title, href, row_date, pdfs, hwps))

                # 목록으로 복귀
                page.goto(list_url, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")

            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


# ════════════════════════════════════════════════════
# 부처별 크롤러
# ════════════════════════════════════════════════════

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
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
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


def crawl_fss(target):
    """금융감독원 — requests"""
    print("\n[금융감독원]")
    s   = new_session()
    BASE = "https://www.fss.or.kr"
    results = []
    for pg in range(1, 4):
        url  = f"{BASE}/fss/bbs/B0000188/list.do?menuNo=200218&pageIndex={pg}"
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
            results.append(make_item("금융감독원", title, href, row_date, pdfs, hwps))
            found += 1
        if found == 0 and pg > 1: break
    return results


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
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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


def crawl_molit(target):
    """국토교통부 — Playwright (링크 prefix 처리)"""
    print("\n[국토교통부]")
    BASE = "https://www.molit.go.kr"
    LIST = f"{BASE}/USR/NEWS/m_71/lst.jsp?lcmspage=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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
                if not href.startswith("http"):
                    if not href.startswith("/"):
                        href = "/USR/NEWS/m_71/" + href
                    href = BASE + href
                if href in seen: continue
                seen.add(href)
                page.goto(href, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("국토교통부", title, href, row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


def crawl_mohw(target):
    """보건복지부 — Playwright (메인 방문 후 목록 접근)"""
    print("\n[보건복지부]")
    BASE = "https://www.mohw.go.kr"
    LIST = f"{BASE}/board.es?mid=a10503000000&bid=0027&nPage=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
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
                full_url = BASE + href if not href.startswith("http") else href
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("보건복지부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


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


def crawl_moj(target):
    """법무부 — Playwright"""
    print("\n[법무부]")
    return pw_crawl_list("법무부",
        "https://www.moj.go.kr/moj/226/subview.do?page=1",
        "https://www.moj.go.kr", target)


def crawl_mcst(target):
    """문화체육관광부 — Playwright (attachFiles 패턴 처리)"""
    print("\n[문화체육관광부]")
    BASE = "https://www.mcst.go.kr"
    LIST = f"{BASE}/kor/s_notice/press/pressList.jsp?pCurrentPage=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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
                # ./pressview.jsp?pSeq=12345 처리
                if href.startswith("./"):
                    href = "/kor/s_notice/press/" + href[2:]
                elif not href.startswith("/") and not href.startswith("http"):
                    href = "/kor/s_notice/press/" + href
                full_url = BASE + href if not href.startswith("http") else href
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("문화체육관광부", title, full_url, row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


def crawl_mois(target):
    """행정안전부 — Playwright (www 없는 도메인 + 메인 방문)"""
    print("\n[행정안전부]")
    BASE = "https://mois.go.kr"
    LIST = f"{BASE}/frt/bbs/type010/commonSelectBoardList.do?bbsId=BBSMSTR_000000000008&pageIndex=1"
    results = []
    target_str = target.strftime("%Y.%m.%d.")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
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
                full_url = BASE + href if not href.startswith("http") else href
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("행정안전부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


def crawl_me(target):
    """환경부 — Playwright"""
    print("\n[환경부]")
    return pw_crawl_list("환경부",
        "https://www.me.go.kr/home/web/board/list.do?menuId=286&boardMasterId=1&boardCategoryId=39&page=1",
        "https://www.me.go.kr", target)


def crawl_moel(target):
    """고용노동부 — Playwright (상대경로 href 처리)"""
    print("\n[고용노동부]")
    BASE     = "https://www.moel.go.kr"
    LIST_URL = f"{BASE}/news/enews/report/enewsList.do?pageIndex=1"
    BASE_DIR = f"{BASE}/news/enews/report/"
    results  = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
                locale="ko-KR", timezone_id="Asia/Seoul",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            page.goto(LIST_URL, wait_until="networkidle", timeout=30000)
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
                # enewsView.do?... 형태 — 절대경로 조합
                if href.startswith("http"):
                    full_url = href
                elif href.startswith("/"):
                    full_url = BASE + href
                else:
                    full_url = BASE_DIR + href
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("고용노동부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST_URL, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


def crawl_mafra(target):
    """농림축산식품부 — Playwright"""
    print("\n[농림축산식품부]")
    return pw_crawl_list("농림축산식품부",
        "https://www.mafra.go.kr/home/5109/subview.do?page=1",
        "https://www.mafra.go.kr", target)


def crawl_mss(target):
    """중소벤처기업부 — Playwright (doBbsFView onclick → View.do)"""
    print("\n[중소벤처기업부]")
    BASE = "https://www.mss.go.kr"
    LIST = f"{BASE}/site/smba/ex/bbs/List.do?cbIdx=86&pageIndex=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
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


def crawl_ftc(target):
    """공정거래위원회 — Playwright"""
    print("\n[공정거래위원회]")
    return pw_crawl_list("공정거래위원회",
        "https://www.ftc.go.kr/www/selectReportUserView.do?key=10&rpttype=1&pageUnit=10&pageIndex=1",
        "https://www.ftc.go.kr", target, skip_main=True)


def crawl_pipc(target):
    """개인정보보호위원회 — Playwright (stealth, 직접 목록 접근)"""
    print("\n[개인정보보호위원회]")
    BASE = "https://www.pipc.go.kr"
    LIST = f"{BASE}/np/cop/bbs/selectBoardList.do?bbsId=BS074&mCode=C020010000&pageIndex=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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
                full_url = BASE + href if not href.startswith("http") else href
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("개인정보보호위원회", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


def crawl_acrc(target):
    """국민권익위원회 — Playwright (올바른 보도자료 URL)"""
    print("\n[국민권익위원회]")
    return pw_crawl_list("국민권익위원회",
        "https://www.acrc.go.kr/board.es?mid=a10402010000&bid=4A&nPage=1",
        "https://www.acrc.go.kr", target)


def crawl_motie(target):
    """산업통상자원부 — Playwright (목록에서 직접 파일 수집, 상세 페이지 접근 없음)"""
    print("\n[산업통상자원부]")
    BASE = "https://www.motie.go.kr"
    LIST = f"{BASE}/kor/article/ATCL3f49a5a8c?pageIndex=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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
                    # Content-Disposition으로 확장자 판별 → 일단 pdf로 시도
                    pdfs.append(full)

                print(f"  ✓ {title[:60]}")
                results.append(make_item("산업통상자원부", title, detail_url,
                                         row_date, pdfs, hwps))
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


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


def crawl_mof(target):
    """해양수산부 — Playwright (fn_selectDoc + jfile 다운로드)"""
    print("\n[해양수산부]")
    BASE = "https://www.mof.go.kr"
    LIST = f"{BASE}/doc/ko/selectDocList.do?menuSeq=971&bbsSeq=10&curPage=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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


def crawl_mogef(target):
    """성평등가족부 — Playwright (메인 방문 후 fn_selectView)"""
    print("\n[성평등가족부]")
    BASE = "https://www.mogef.go.kr"
    LIST = f"{BASE}/nw/rpd/nw_rpd_s001.do?mid=news405&page=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
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

            for row in soup.select("table tbody tr"):
                text = row.get_text(" ", strip=True)
                dm   = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                if not dm: continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date < target.isoformat(): continue
                if row_date != target.isoformat(): continue
                a = row.find("a", href=True)
                if not a: continue
                onclick = a.get("onclick", "") or a.get("href", "")
                seq_m   = re.search(r"fn_selectView\('(\d+)'\)", onclick)
                if not seq_m: continue
                full_url = f"{BASE}/nw/rpd/nw_rpd_s001d.do?mid=news405&bbtSn={seq_m.group(1)}"
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("성평등가족부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


def crawl_mpva(target):
    """국가보훈부 — Playwright (./selectBbsNttView.do → /mpva/selectBbsNttView.do)"""
    print("\n[국가보훈부]")
    BASE = "https://www.mpva.go.kr"
    LIST = f"{BASE}/mpva/selectBbsNttList.do?bbsNo=16&key=77&pageIndex=1"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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

            for row in soup.select("table tbody tr"):
                text = row.get_text(" ", strip=True)
                dm   = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                if not dm: continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date < target.isoformat(): continue
                if row_date != target.isoformat(): continue
                a = row.find("a", href=True)
                if not a: continue
                href = re.sub(r";jsessionid=[^?&]*", "", a["href"])
                # ./selectBbsNttView.do → /mpva/selectBbsNttView.do
                if href.startswith("./"):
                    href = "/mpva/" + href[2:]
                elif not href.startswith("/") and not href.startswith("http"):
                    href = "/mpva/" + href
                full_url = BASE + href if not href.startswith("http") else href
                if full_url in seen: continue
                seen.add(full_url)
                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")
                pdfs, hwps = extract_file_links(soup2, BASE)
                title = clean_title(a.get_text(strip=True))
                print(f"  ✓ {title[:60]}")
                results.append(make_item("국가보훈부", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")
            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


def crawl_moleg(target):
    """법제처 — Playwright (직접 목록 접근)"""
    print("\n[법제처]")
    return pw_crawl_list("법제처",
        "https://www.moleg.go.kr/board.es?mid=a10501000000&bid=0048&nPage=1",
        "https://www.moleg.go.kr", target, skip_main=True)


def crawl_mpm(target):
    """인사혁신처 — Playwright (boardDownload 패턴)"""
    print("\n[인사혁신처]")
    return pw_crawl_list("인사혁신처",
        "https://www.mpm.go.kr/mpm/comm/newsPress/newsPressRelease/?pageIndex=1",
        "https://www.mpm.go.kr", target)


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
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
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
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
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


def crawl_bok(target):
    """한국은행 — Playwright (a.title + span.date + /fileSrc/ 다운로드)"""
    print("\n[한국은행]")
    BASE = "https://www.bok.or.kr"
    LIST = f"{BASE}/portal/singl/newsData/list.do?menuNo=201263"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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

            for a in soup.find_all("a", class_="title"):
                href = a["href"]
                title = clean_title(a.get_text(strip=True))
                # 날짜: 부모에서 span.date 찾기
                parent = a.find_parent()
                date_span = None
                for _ in range(4):
                    if not parent: break
                    date_span = parent.find("span", class_="date")
                    if date_span: break
                    parent = parent.find_parent()
                if not date_span: continue
                date_text = re.sub(r"등록일", "", date_span.get_text(strip=True))
                dm = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", date_text)
                if not dm: continue
                row_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                if row_date < target.isoformat(): continue
                if row_date != target.isoformat(): continue

                full_url = BASE + href if not href.startswith("http") else href
                if full_url in seen: continue
                seen.add(full_url)

                page.goto(full_url, wait_until="networkidle", timeout=30000)
                soup2 = BeautifulSoup(page.content(), "lxml")

                # 파일: /fileSrc/ 패턴
                pdfs, hwps, seen2 = [], [], set()
                for a2 in soup2.find_all("a", href=re.compile(r"/fileSrc/")):
                    h2 = a2["href"]
                    fn = a2.get_text(strip=True).lower()
                    if "뷰어" in fn or "viewer" in fn.lower(): continue
                    full2 = BASE + h2 if not h2.startswith("http") else h2
                    if full2 in seen2: continue
                    seen2.add(full2)
                    if re.search(r"\.pdf", fn): pdfs.append(full2)
                    elif re.search(r"\.hwp", fn): hwps.append(full2)

                print(f"  ✓ {title[:60]}")
                results.append(make_item("한국은행", title, full_url,
                                         row_date, pdfs, hwps))
                page.goto(LIST, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "lxml")

            browser.close()
    except Exception as e:
        print(f"  [Playwright 오류] {e}")
    return results


# ════════════════════════════════════════════════════
# 파일 다운로드
# ════════════════════════════════════════════════════

def download_file(url, filename, session):
    """파일 다운로드 — Content-Disposition으로 실제 확장자 판별"""
    path = PDF_DIR / filename
    if path.exists():
        print(f"    [스킵] {filename}")
        return path
    try:
        r = session.get(url, timeout=30, stream=True)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "html" in ct:
            print(f"    [스킵] HTML 응답")
            return None

        # Content-Disposition에서 실제 파일명 추출
        cd = r.headers.get("Content-Disposition", "")
        cd_name = ""
        m = re.search(r"filename[^=]*=([^;\n]+)", cd, re.I)
        if m:
            cd_name = m.group(1).strip().lower()
            # 확장자 교정
            stem = Path(filename).stem
            if cd_name.endswith(".pdf"):
                filename = stem + ".pdf"
            elif re.search(r"\.hwp", cd_name):
                filename = stem + (".hwpx" if cd_name.endswith(".hwpx") else ".hwp")
            path = PDF_DIR / filename

        if path.exists():
            print(f"    [스킵] {filename}")
            return path

        with open(path, "wb") as f:
            for chunk in r.iter_content(8192): f.write(chunk)
        print(f"    저장: {filename} ({path.stat().st_size//1024}KB)")
        return path
    except Exception as e:
        print(f"    다운로드 오류: {e}")
        return None


# ════════════════════════════════════════════════════
# 텍스트 추출
# ════════════════════════════════════════════════════

def clean_hwp_text(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(path):
    try:
        texts = []
        with pdfplumber.open(path) as pdf:
            for pg in pdf.pages:
                t = pg.extract_text()
                if t: texts.append(t)
        text = "\n".join(texts)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except Exception as e:
        print(f"    PDF 추출 오류: {e}")
        return ""


def extract_hwp(path):
    """HWP(OLE2) / HWPX(ZIP) 텍스트 추출"""
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        # HWPX — ZIP 기반
        if magic[:2] == b"PK":
            with zipfile.ZipFile(path) as z:
                files = z.namelist()
                if "Preview/PrvText.txt" in files:
                    text = z.read("Preview/PrvText.txt").decode("utf-8", errors="ignore")
                    return clean_hwp_text(text)
                sections = sorted(f for f in files
                                  if re.match(r"Contents/section\d+\.xml", f))
                parts = []
                for sec in sections:
                    xml = z.read(sec).decode("utf-8", errors="ignore")
                    parts.extend(re.findall(r"<hp:t[^>]*>([^<]+)</hp:t>", xml))
                return clean_hwp_text(" ".join(parts))
        # HWP — OLE2 기반
        ole = olefile.OleFileIO(str(path))
        if ole.exists("PrvText"):
            raw  = ole.openstream("PrvText").read()
            text = raw.decode("utf-16-le", errors="ignore")
            ole.close()
            return clean_hwp_text(text)
        texts = []
        for i in range(10):
            sec = f"BodyText/Section{i}"
            if not ole.exists(sec): break
            raw = ole.openstream(sec).read()
            try: raw = zlib.decompress(raw, -15)
            except: pass
            texts.append(raw.decode("utf-16-le", errors="ignore"))
        ole.close()
        return clean_hwp_text("\n".join(texts))
    except Exception as e:
        print(f"    HWP 추출 오류: {e}")
        return ""


def save_text(item, text):
    src   = re.sub(r"[^\w가-힣]", "", item["source"])[:4]
    safe  = re.sub(r"[^\w가-힣]", "_", item["title"])[:30]
    fname = f"{item['date']}_{src}_{safe}.txt"
    path  = TXT_DIR / fname
    content = (f"[출처] {item['source']}\n[제목] {item['title']}\n"
               f"[날짜] {item['date']}\n[URL]  {item['url']}\n"
               f"{'─'*60}\n{text}\n")
    path.write_text(content, encoding="utf-8")
    print(f"    텍스트 저장: {fname} ({len(text)}자)")
    return path


def process_item(item):
    """PDF 우선 다운로드 → HWP → 텍스트 추출 → txt 저장"""
    s    = new_session()
    src  = re.sub(r"[^\w가-힣]", "", item["source"])[:4]
    safe = re.sub(r"[^\w가-힣]", "_", item["title"])[:25]

    # 기존 txt 파일 있으면 텍스트 바로 로드
    txt_fname = f"{item['date']}_{src}_{safe}.txt"
    txt_path  = TXT_DIR / txt_fname
    if txt_path.exists():
        raw = txt_path.read_text(encoding="utf-8")
        # 헤더 제거 후 본문만 추출
        sep = "─" * 60
        if sep in raw:
            item["text"] = raw.split(sep, 1)[-1].strip()
        else:
            item["text"] = raw
        return

    # PDF 우선 (이미 있으면 텍스트만 추출)
    texts = []
    for j, url in enumerate(item["pdfs"], 1):
        fname = f"{item['date']}_{src}_{safe}_{j}.pdf"
        path  = download_file(url, fname, s)
        if not path: continue
        text  = extract_pdf(path)
        if text:
            item["files"].append(str(path))
            texts.append(text)
        time.sleep(0.3)

    if texts:
        item["text"] = "\n\n".join(texts)
        save_text(item, item["text"])
        return

    # HWP 폴백
    if item["hwps"]:
        print(f"    PDF 없음 → HWP 시도")
    for j, url in enumerate(item["hwps"], 1):
        ext   = "hwpx" if "hwpx" in url.lower() else "hwp"
        fname = f"{item['date']}_{src}_{safe}_{j}.{ext}"
        path  = download_file(url, fname, s)
        if not path: continue
        text  = extract_hwp(path)
        if text:
            item["files"].append(str(path))
            texts.append(text)
        time.sleep(0.3)

    if texts:
        item["text"] = "\n\n".join(texts)
        save_text(item, item["text"])

    if not item["text"]:
        print(f"    ⚠ 텍스트 추출 실패 (PDF:{len(item['pdfs'])} HWP:{len(item['hwps'])})")


# ════════════════════════════════════════════════════
# LLM 요약
# ════════════════════════════════════════════════════

def summarize(item):
    if not item["text"]:
        return "[텍스트 없음]"
    text = item["text"][:MAX_TEXT]
    if len(item["text"]) > MAX_TEXT:
        text += "\n\n[이하 생략]"
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content":
                     f"기관: {item['source']}\n제목: {item['title']}\n\n---\n{text}"},
                ],
                "stream": False,
                "temperature": 0.3,
            },
            timeout=120,
        )
        if resp.status_code == 429: return "[한도 초과]"
        if resp.status_code != 200: return f"[오류] HTTP {resp.status_code}"
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[요약 실패] {e}"


# ════════════════════════════════════════════════════
# 크롤러 목록 & 메인
# ════════════════════════════════════════════════════

CRAWLERS = [
    ("금융위원회",       crawl_fsc),
    ("금융감독원",       crawl_fss),
    ("기획재정부",       crawl_moef),
    ("교육부",           crawl_moe),
    ("국토교통부",       crawl_molit),
    ("보건복지부",       crawl_mohw),
    ("통일부",           crawl_unikorea),
    ("법무부",           crawl_moj),
    ("문화체육관광부",   crawl_mcst),
    ("행정안전부",       crawl_mois),
    ("환경부",           crawl_me),
    ("고용노동부",       crawl_moel),
    ("농림축산식품부",   crawl_mafra),
    ("중소벤처기업부",   crawl_mss),
    ("공정거래위원회",   crawl_ftc),
    ("개인정보보호위원회", crawl_pipc),
    ("국민권익위원회",   crawl_acrc),
    ("산업통상자원부",   crawl_motie),
    ("외교부",           crawl_mofa),
    ("해양수산부",       crawl_mof),
    ("성평등가족부",     crawl_mogef),
    ("국가보훈부",       crawl_mpva),
    ("법제처",           crawl_moleg),
    ("인사혁신처",       crawl_mpm),
    ("과학기술정보통신부", crawl_msit),
    ("국방부",           crawl_mnd),
    ("한국은행",           crawl_bok),
]



_posted_titles: set = set()

def wp_check_duplicate(title: str, date_str: str) -> bool:
    key = f"{date_str}::{title.strip()}"
    if key in _posted_titles:
        print(f"    [중복 스킵] {title[:40]}")
        return True
    try:
        import html as _html
        after  = f"{date_str}T00:00:00"
        before = f"{date_str}T23:59:59"
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"after": after, "before": before,
                    "per_page": 100, "_fields": "id,title"},
            auth=(WP_USER, WP_PASS), timeout=10,
        )
        if r.status_code != 200: return False
        for p in r.json():
            existing = _html.unescape(
                p.get("title", {}).get("rendered", "")).strip()
            if existing == title.strip():
                print(f"    [중복 스킵] #{p['id']} {title[:40]}")
                _posted_titles.add(key)
                return True
        return False
    except:
        return False


def wp_post(item):
    if not item.get("summary") or item["summary"].startswith("["):
        return False

    # 중복 체크
    if wp_check_duplicate(item["title"], item["date"]):
        return False

    summary = ""
    keywords = []
    for line in item["summary"].split("\n"):
        if line.startswith("요약:"):
            summary = line.replace("요약:", "").strip()
        elif line.startswith("키워드:"):
            keywords = [k.strip() for k in line.replace("키워드:", "").split(",")]

    cat_name = CAT_MAP.get(item["source"], "브리핑룸")
    cat_ids  = [
        wp_get_or_create_category("브리핑룸"),
        wp_get_or_create_category(cat_name),
    ]

    file_links = ""
    for f in item.get("files", []):
        fname = Path(f).name
        file_links += f'<li><a href="{item["url"]}" target="_blank">📎 {fname}</a></li>'

    kw_html = ""
    if keywords:
        kw_html = '<div class="briefing-keywords">' + \
                  " ".join(f"<span>#{k}</span>" for k in keywords) + "</div>"

    content_html = f"""
<div class="briefing-post">
  <div class="briefing-meta">
    <span class="briefing-source">🏛 {item["source"]}</span>
    <span class="briefing-date">📅 {item["date"]}</span>
  </div>
  <div class="briefing-summary">
    <h3>📋 AI 요약</h3>
    <p>{summary}</p>
  </div>
  {kw_html}
  <div class="briefing-links">
    <h4>🔗 원문 및 첨부파일</h4>
    <ul>
      <li><a href="{item["url"]}" target="_blank">↗ 원문 보기</a></li>
      {file_links}
    </ul>
  </div>
</div>
"""

    # 태그 ID 생성/조회
    tag_ids = []
    for kw in keywords:
        if not kw: continue
        try:
            r_tag = requests.get(f"{WP_URL}/wp-json/wp/v2/tags",
                                 params={"search": kw, "per_page": 3},
                                 auth=(WP_USER, WP_PASS), timeout=10)
            found = [t for t in r_tag.json() if t["name"] == kw]
            if found:
                tag_ids.append(found[0]["id"])
            else:
                r_new = requests.post(f"{WP_URL}/wp-json/wp/v2/tags",
                                      json={"name": kw},
                                      auth=(WP_USER, WP_PASS), timeout=10)
                if r_new.status_code in (200, 201):
                    tag_ids.append(r_new.json().get("id"))
        except:
            pass

    payload = {
        "title":      item["title"],
        "content":    content_html,
        "status":     "publish",
        "categories": cat_ids,
        "tags":       tag_ids,
    }

    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
                          json=payload, auth=(WP_USER, WP_PASS), timeout=30)
        if r.status_code in (200, 201):
            post_id  = r.json().get("id")
            post_url = r.json().get("link")
            print(f"    ✅ WP #{post_id} {post_url}")
            return True
        else:
            print(f"    ❌ WP 오류: {r.status_code} {r.text[:100]}")
            return False
    except Exception as e:
        print(f"    ❌ WP 예외: {e}")
        return False


def main():
    target = date.today()
    if len(sys.argv) > 1:
        try:
            target = date.fromisoformat(sys.argv[1])
        except ValueError:
            print("날짜 형식 오류. 예: python briefing.py 2026-03-18")
            sys.exit(1)

    print(f"{'='*60}")
    print(f"  브리핑룸  |  {target}  |  {len(CRAWLERS)}개 부처")
    print(f"{'='*60}")

    all_items = []
    for name, crawler in CRAWLERS:
        try:
            items = crawler(target)
            print(f"  → {name}: {len(items)}건")
            all_items.extend(items)
        except Exception as e:
            print(f"  [{name}] 오류: {e}")

    print(f"\n{'─'*60}")
    print(f"총 {len(all_items)}건 수집\n")

    # 파일 처리
    print("[파일 처리 중...]")
    for item in all_items:
        if not (item["pdfs"] or item["hwps"]): continue
        print(f"\n  [{item['source']}] {item['title'][:50]}")
        print(f"  PDF:{len(item['pdfs'])} HWP:{len(item['hwps'])}")
        process_item(item)

    # LLM 요약
    print(f"\n{'─'*60}")
    print("[LLM 요약 중...]")
    for item in all_items:
        item["summary"] = summarize(item)
        print(f"  [{item['source']}] {item['summary'][:70]}")
        time.sleep(0.5)

    # WordPress 자동 포스팅
    print(f"\n{'─'*60}")
    print("[WordPress 포스팅 중...]")
    wp_count = 0
    for item in all_items:
        if item.get("summary") and not item["summary"].startswith("["):
            if wp_post(item):
                wp_count += 1
            time.sleep(1)
    print(f"  ✅ WordPress 포스팅 완료: {wp_count}건")

    # 최종 출력
    print(f"\n{'='*60}")
    print(f"  완료  |  {target}  |  총 {len(all_items)}건")
    print(f"{'='*60}")
    by_source = {}
    for item in all_items:
        by_source.setdefault(item["source"], []).append(item)

    print(f"\n{'─'*60}")
    total = 0
    for name, _ in CRAWLERS:
        cnt   = len(by_source.get(name, []))
        total += cnt
        mark  = "✅" if cnt > 0 else "⚪"
        print(f"  {mark} {name:<18} {cnt}건")
    print(f"{'─'*60}")
    print(f"  합계: {total}건")
    print(f"  파일: {PDF_DIR}")
    print(f"  텍스트: {TXT_DIR}")


if __name__ == "__main__":
    main()

# ════════════════════════════════════════════════════
# WordPress 자동 포스팅
# ════════════════════════════════════════════════════

WP_URL  = "https://hotclipfolio.com"
WP_USER = "hotclipfolio"
WP_PASS = "qSUw w4xA ELSm w6z9 6zIU U8G8"

CAT_MAP = {
    "금융위원회": "금융경제", "금융감독원": "금융경제",
    "기획재정부": "금융경제", "한국은행": "금융경제",
    "산업통상자원부": "금융경제", "공정거래위원회": "금융경제",
    "보건복지부": "사회복지", "교육부": "사회복지",
    "고용노동부": "사회복지", "성평등가족부": "사회복지",
    "국민권익위원회": "사회복지", "국가보훈부": "사회복지",
    "법무부": "사회복지",
    "과학기술정보통신부": "산업기술", "국토교통부": "산업기술",
    "해양수산부": "산업기술", "농림축산식품부": "산업기술",
    "중소벤처기업부": "산업기술", "환경부": "산업기술",
    "개인정보보호위원회": "산업기술",
    "외교부": "외교안보", "국방부": "외교안보", "통일부": "외교안보",
    "행정안전부": "행정법제", "인사혁신처": "행정법제",
    "법제처": "행정법제", "문화체육관광부": "행정법제",
}

_wp_cat_cache = {}

def wp_get_or_create_category(name):
    if name in _wp_cat_cache:
        return _wp_cat_cache[name]
    auth = (WP_USER, WP_PASS)
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories",
                     params={"search": name, "per_page": 5}, auth=auth, timeout=10)
    for cat in r.json():
        if cat["name"] == name:
            _wp_cat_cache[name] = cat["id"]
            return cat["id"]
    r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/categories",
                       json={"name": name}, auth=auth, timeout=10)
    cat_id = r2.json().get("id", 1)
    _wp_cat_cache[name] = cat_id
    return cat_id

