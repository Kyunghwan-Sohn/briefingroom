from __future__ import annotations

import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from briefingroom.config import HEADERS, TIMEOUT, DELAY, PROXIES, PROXY_URL


def make_item(source, title, url, date_str, pdfs, hwps):
    return {
        "source": source, "title": title, "url": url,
        "date": date_str,
        "pdfs": list(dict.fromkeys(pdfs)),
        "hwps": list(dict.fromkeys(hwps)),
        "files": [], "text": "", "body_text": "", "summary": "",
    }


def new_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    if PROXIES:
        s.proxies.update(PROXIES)
    return s


def pw_proxy_arg():
    """Playwright용 프록시 설정 반환"""
    if not PROXY_URL:
        return {}
    return {"proxy": {"server": PROXY_URL}}


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
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
                **pw_proxy_arg())
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"),
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
                except Exception:
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
