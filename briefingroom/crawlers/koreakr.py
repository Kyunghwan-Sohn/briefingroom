"""korea.kr 정책브리핑 통합 크롤러

requests만으로 동작 (Playwright 불필요, IP 차단 없음).
모든 부처 보도자료를 한 곳에서 수집.
"""
from __future__ import annotations

import re
import ssl
import time
from datetime import date

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from briefingroom.config import HEADERS, PROXIES, DELAY


BASE = "https://www.korea.kr"

# korea.kr SSL 호환 어댑터 (TLS 1.2+ 강제, 레거시 cipher 허용)
class _TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def _new_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.mount("https://", _TLSAdapter(max_retries=3))
    if PROXIES:
        s.proxies.update(PROXIES)
    return s


def _clean_title(title: str) -> str:
    """제목에서 불필요한 부분 제거 — 제목만 추출"""
    # 1. 불필요한 본문 키워드 이후 잘라내기
    for cut in ["관련 보도자료", "관련  보도자료", "*자세한 내용은",
                 "□ ", "○ ", "◈ ", "※ "]:
        idx = title.find(cut)
        if idx > 10:
            title = title[:idx]

    # 2. 날짜+부처명 꼬리 제거 (예: '2026.03.18금융위원회')
    title = re.sub(r"\d{4}\.\d{2}\.\d{2}[\w가-힣]*$", "", title)

    # 3. 제목 반복 제거 (예: "제목제목본문..." → "제목")
    title = title.strip()
    half = len(title) // 2
    if half > 15 and title[:half].strip() == title[half:half * 2].strip():
        title = title[:half].strip()

    # 4. 부처명(장관 ...) 이후 본문 시작 패턴 제거
    title = re.sub(r"(부|청|처|원|위원회|실)\((?:장관|청장|처장|위원장|실장)\s+[\w가-힣]+(?:,\s*이하\s+[\w가-힣]+)?\).*$", r"\1", title)

    # 5. 줄바꿈/특수공백 정리
    title = re.sub(r"[\r\n\t]+", " ", title)
    title = re.sub(r"\s{2,}", " ", title).strip()

    # 6. "- 부제" 패턴: 첫 번째 "- "에서 자르되, 본문이 시작되는 패턴인 경우만
    dash_idx = title.find("- ")
    if dash_idx > 10 and len(title) > 80:
        after_dash = title[dash_idx + 2:]
        # 부제가 아닌 본문 시작 패턴 (날짜, 부처명+은/는 등)
        if re.match(r"(\d+월|\d{4}년|['']?\d{2}년|지난|올해|금일|오늘|내일)", after_dash):
            title = title[:dash_idx].strip()
        elif len(title) > 120:
            title = title[:dash_idx].strip()

    # 7. 최종 길이 제한 (70자 — 깔끔한 제목 기준)
    if len(title) > 70:
        # 문장 경계에서 자르기 시도
        for sep in [", ", "…", "·", " "]:
            cut = title.rfind(sep, 0, 70)
            if cut > 30:
                title = title[:cut].strip()
                break
        else:
            title = title[:67] + "..."

    return title.strip().rstrip(".")


def _parse_list_page(soup: BeautifulSoup, target_date: str):
    """목록 페이지에서 보도자료 아이템 추출"""
    items = []
    for li in soup.find_all("li"):
        a = li.find("a", href=lambda h: h and "pressReleaseView" in h)
        if not a:
            continue

        spans = li.find_all("span")
        span_texts = [sp.get_text(strip=True) for sp in spans if sp.get_text(strip=True)]

        # 마지막 span들에서 날짜, 부처 추출
        date_str = None
        source = None
        for sp in reversed(span_texts):
            if not date_str and re.match(r"^\d{4}\.\d{2}\.\d{2}$", sp):
                date_str = sp
            elif not source and re.match(r"^[\w가-힣]{2,}$", sp) and sp != date_str:
                source = sp

        if not date_str or not source:
            continue

        iso_date = date_str.replace(".", "-")
        if iso_date != target_date:
            # 날짜가 target보다 이전이면 'older' 표시
            if iso_date < target_date:
                items.append({"_older": True})
            continue

        # newsId 추출
        href = a.get("href", "")
        nid_m = re.search(r"newsId=(\d+)", href)
        if not nid_m:
            continue
        news_id = nid_m.group(1)

        # 제목 추출: span.text에서 span.lead 부분을 제거
        text_span = a.find("span", class_="text")
        lead_span = a.find("span", class_="lead")
        if text_span and lead_span:
            full = text_span.get_text(strip=True)
            lead = lead_span.get_text(strip=True)
            # full에서 lead가 시작되는 지점까지가 제목
            idx = full.find(lead[:30]) if lead else -1
            title = full[:idx].strip() if idx > 5 else full[:80]
        elif text_span:
            title = text_span.get_text(strip=True)[:80]
        else:
            title = a.get_text(strip=True).split("\n")[0][:80]
        title = _clean_title(title)
        if len(title) > 120:
            title = title[:117] + "..."

        # 상세 URL
        detail_url = f"{BASE}/briefing/pressReleaseView.do?newsId={news_id}"

        items.append({
            "source": source,
            "title": title,
            "url": detail_url,
            "date": iso_date,
            "news_id": news_id,
        })

    return items


def _fetch_detail(session, news_id: str):
    """상세 페이지에서 첨부파일 URL + 본문 텍스트 추출"""
    url = f"{BASE}/briefing/pressReleaseView.do?newsId={news_id}"
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return [], [], ""
        soup = BeautifulSoup(r.text, "lxml")
    except Exception:
        return [], [], ""

    pdfs, hwps, seen = [], [], set()
    for a in soup.find_all("a", href=re.compile(r"/common/download\.do")):
        href = a["href"].replace("&amp;", "&")
        full = BASE + href if not href.startswith("http") else href
        if full in seen:
            continue
        seen.add(full)
        fn = a.get_text(strip=True).lower()
        if re.search(r"\.pdf", fn):
            pdfs.append(full)
        elif re.search(r"\.hwp", fn):
            hwps.append(full)
        else:
            # 확장자 불명 — 기본 PDF로
            pdfs.append(full)

    # HTML 본문 텍스트 추출
    body_text = ""
    # korea.kr 상세 페이지 본문 영역 셀렉터 (우선순위)
    for sel in [
        "div.view_cont",       # korea.kr 표준 본문 영역
        "div.article_view",
        "div.detailCont",
        "div#contentView",
        "div.content_view",
        "article",
        "div.content",
        "main",
    ]:
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > 50:
            # 불필요한 요소 제거
            for tag in el.find_all(["script", "style", "nav", "footer", "iframe"]):
                tag.decompose()
            body_text = re.sub(r"\s+", " ", el.get_text(strip=True))[:6000]
            break

    # og:description 폴백
    if not body_text or len(body_text) < 30:
        og = soup.find("meta", property="og:description")
        if og and og.get("content") and len(og["content"]) > 30:
            body_text = og["content"]

    return pdfs, hwps, body_text


def crawl_koreakr(target: date) -> list[dict]:
    """korea.kr에서 특정 날짜의 전체 부처 보도자료 수집"""
    print(f"\n[korea.kr] {target} 보도자료 수집")
    s = _new_session()
    target_str = target.isoformat()
    all_items = []
    seen_ids = set()

    for page in range(1, 50):
        url = (f"{BASE}/briefing/pressReleaseList.do"
               f"?pageIndex={page}"
               f"&startDate={target_str}&endDate={target_str}")
        try:
            r = s.get(url, timeout=15)
            if r.status_code != 200:
                print(f"  HTTP {r.status_code} at page {page}")
                break
        except Exception as e:
            print(f"  [요청 오류] {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        items = _parse_list_page(soup, target_str)

        if not items:
            break

        new_count = 0
        older_count = 0
        for item in items:
            if item.get("_older"):
                older_count += 1
                continue
            if item["news_id"] in seen_ids:
                continue
            seen_ids.add(item["news_id"])

            # 첨부파일 + 본문 텍스트 수집
            pdfs, hwps, body_text = _fetch_detail(s, item["news_id"])
            time.sleep(0.3)

            result = {
                "source": item["source"],
                "title": item["title"],
                "url": item["url"],
                "date": item["date"],
                "pdfs": pdfs,
                "hwps": hwps,
                "files": [],
                "text": "",
                "body_text": body_text,
                "summary": "",
            }
            all_items.append(result)
            new_count += 1

        print(f"  page {page}: {new_count}건 수집")

        # 모든 아이템이 이전 날짜면 종료
        if older_count > 0 and new_count == 0:
            break

        time.sleep(DELAY)

    print(f"  → korea.kr 총 {len(all_items)}건 수집 완료")

    # 부처별 통계
    from collections import Counter
    stats = Counter(item["source"] for item in all_items)
    for source, cnt in stats.most_common():
        print(f"    {source}: {cnt}건")

    return all_items
