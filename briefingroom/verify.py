"""포스팅 전 검증: 기관별 실제 보도자료 수 vs 수집 수 비교

각 기관의 웹사이트에서 실제 보도자료 개수를 확인하고,
수집 건수와 비교하여 누락분을 재크롤링합니다.
"""
from __future__ import annotations

import re
import ssl
import time
from collections import Counter
from datetime import date

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class _TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def _session():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"})
    s.mount("https://", _TLSAdapter(max_retries=2))
    return s


# ═══════════════════════════════════════════════════════════
# 기관별 실제 건수 확인 함수
# ═══════════════════════════════════════════════════════════

def _count_koreakr(s, target: date, source_name: str) -> int | None:
    """korea.kr에서 특정 부처의 해당 날짜 보도자료 건수"""
    ds = target.isoformat()
    count = 0
    for pg in range(1, 15):
        try:
            r = s.get(f"https://www.korea.kr/briefing/pressReleaseList.do"
                      f"?pageIndex={pg}&startDate={ds}&endDate={ds}", timeout=15)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "lxml")
            found = 0
            for li in soup.find_all("li"):
                a = li.find("a", href=lambda h: h and "pressReleaseView" in h)
                if not a:
                    continue
                spans = [sp.get_text(strip=True) for sp in li.find_all("span") if sp.get_text(strip=True)]
                src = None
                for sp in reversed(spans):
                    if re.match(r"^[\w가-힣]{2,}$", sp) and not re.match(r"^\d", sp):
                        src = sp
                        break
                if src == source_name:
                    count += 1
                    found += 1
            if found == 0 and pg > 2:
                break
        except Exception:
            break
    return count


def _count_fss(s, target: date) -> int:
    """금융감독원 실제 건수"""
    count = 0
    ds = target.isoformat()
    for pg in range(1, 5):
        try:
            r = s.get(f"https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218&pageIndex={pg}", timeout=15)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "lxml")
            for row in soup.select("table tbody tr"):
                text = row.get_text(" ", strip=True)
                dm = re.search(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", text)
                if dm:
                    rd = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
                    if rd == ds:
                        count += 1
                    elif rd < ds:
                        return count
        except Exception:
            break
    return count


# 검증 가능한 기관 목록 (korea.kr에서 확인 가능)
VERIFIABLE_SOURCES = [
    "금융위원회", "기획재정부", "재정경제부", "교육부", "보건복지부",
    "고용노동부", "국토교통부", "외교부", "과학기술정보통신부", "행정안전부",
    "산업통상자원부", "산업통상부", "농림축산식품부", "문화체육관광부",
    "법무부", "국방부", "환경부", "기후에너지환경부", "해양수산부",
    "중소벤처기업부", "통일부", "경찰청", "소방청", "산림청",
]


def verify_counts(items: list[dict], target: date) -> dict:
    """수집 건수 vs 실제 건수 비교. 누락 기관 리스트 반환."""
    print(f"\n{'━' * 60}")
    print(f"  검증: 기관별 수집 건수 vs 실제 건수")
    print(f"{'━' * 60}")

    s = _session()
    collected = Counter(item["source"] for item in items)
    mismatches = {}  # source → (collected, actual)

    # 주요 기관 korea.kr 대비 검증
    for source in VERIFIABLE_SOURCES:
        my_count = collected.get(source, 0)
        try:
            actual = _count_koreakr(s, target, source)
            if actual is None:
                continue
            diff = actual - my_count
            if diff > 0:
                mismatches[source] = (my_count, actual)
                print(f"  ⚠️  {source:<18} 수집 {my_count}건 / 실제 {actual}건 (누락 {diff}건)")
            elif my_count > 0:
                print(f"  ✅ {source:<18} {my_count}건 일치")
        except Exception:
            pass
        time.sleep(0.3)

    # 금융감독원 개별 검증
    fss_my = collected.get("금융감독원", 0)
    try:
        fss_actual = _count_fss(s, target)
        if fss_actual > fss_my:
            mismatches["금융감독원"] = (fss_my, fss_actual)
            print(f"  ⚠️  {'금융감독원':<18} 수집 {fss_my}건 / 실제 {fss_actual}건 (누락 {fss_actual - fss_my}건)")
        elif fss_my > 0:
            print(f"  ✅ {'금융감독원':<18} {fss_my}건 일치")
    except Exception:
        pass

    if not mismatches:
        print(f"\n  ✅ 모든 기관 건수 일치!")
    else:
        total_missing = sum(actual - my for my, actual in mismatches.values())
        print(f"\n  ⚠️  {len(mismatches)}개 기관에서 총 {total_missing}건 누락 감지")

    return mismatches


def fill_missing(items: list[dict], mismatches: dict, target: date) -> list[dict]:
    """누락된 기관의 보도자료를 재크롤링하여 보완"""
    if not mismatches:
        return items

    print(f"\n{'━' * 60}")
    print(f"  누락분 재크롤링 ({len(mismatches)}개 기관)")
    print(f"{'━' * 60}")

    from briefingroom.crawlers import CRAWLERS
    crawler_map = dict(CRAWLERS)

    existing_keys = {(it["title"].strip(), it["date"]) for it in items}
    added = 0

    for source, (my_count, actual) in mismatches.items():
        # korea.kr에서 해당 기관 보도자료 재수집
        s = _session()
        ds = target.isoformat()
        new_items = []

        for pg in range(1, 15):
            try:
                r = s.get(f"https://www.korea.kr/briefing/pressReleaseList.do"
                          f"?pageIndex={pg}&startDate={ds}&endDate={ds}", timeout=15)
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, "lxml")
                found = 0
                for li in soup.find_all("li"):
                    a = li.find("a", href=lambda h: h and "pressReleaseView" in h)
                    if not a:
                        continue
                    spans = li.find_all("span")
                    span_texts = [sp.get_text(strip=True) for sp in spans if sp.get_text(strip=True)]
                    dt = src = None
                    for sp in reversed(span_texts):
                        if not dt and re.match(r"^\d{4}\.\d{2}\.\d{2}$", sp):
                            dt = sp
                        elif not src and re.match(r"^[\w가-힣]{2,}$", sp) and sp != dt:
                            src = sp
                    if src != source or not dt:
                        continue
                    iso = dt.replace(".", "-")
                    if iso != ds:
                        continue

                    title = a.get_text(strip=True)
                    for cut in ["관련 보도자료", "*자세한"]:
                        idx = title.find(cut)
                        if idx > 10:
                            title = title[:idx]
                    title = re.sub(r"\d{4}\.\d{2}\.\d{2}.*$", "", title).strip().rstrip(".")

                    nid_m = re.search(r"newsId=(\d+)", a.get("href", ""))
                    if not nid_m:
                        continue
                    detail_url = f"https://www.korea.kr/briefing/pressReleaseView.do?newsId={nid_m.group(1)}"

                    key = (title.strip(), iso)
                    if key in existing_keys:
                        continue

                    # 첨부파일 수집
                    pdfs, hwps = [], []
                    try:
                        r2 = s.get(detail_url, timeout=15)
                        if r2.status_code == 200:
                            soup2 = BeautifulSoup(r2.text, "lxml")
                            for a2 in soup2.find_all("a", href=re.compile(r"/common/download\.do")):
                                href = a2["href"].replace("&amp;", "&")
                                full = "https://www.korea.kr" + href if not href.startswith("http") else href
                                fn = a2.get_text(strip=True).lower()
                                if re.search(r"\.pdf", fn):
                                    pdfs.append(full)
                                elif re.search(r"\.hwp", fn):
                                    hwps.append(full)
                                else:
                                    pdfs.append(full)
                    except Exception:
                        pass

                    new_items.append({
                        "source": source, "title": title, "url": detail_url,
                        "date": iso, "pdfs": pdfs, "hwps": hwps,
                        "files": [], "text": "", "summary": "",
                    })
                    existing_keys.add(key)
                    found += 1
                if found == 0 and pg > 3:
                    break
            except Exception:
                break
            time.sleep(0.3)

        # 개별 크롤러로도 시도
        if len(new_items) < (actual - my_count) and source in crawler_map:
            try:
                crawler_items = crawler_map[source](target)
                for ci in crawler_items:
                    key = (ci["title"].strip(), ci["date"])
                    if key not in existing_keys:
                        new_items.append(ci)
                        existing_keys.add(key)
            except Exception:
                pass

        if new_items:
            items.extend(new_items)
            added += len(new_items)
            print(f"  → {source}: +{len(new_items)}건 보완 (총 {my_count + len(new_items)}/{actual}건)")
        else:
            print(f"  → {source}: 추가 수집 실패")

    print(f"\n  보완 완료: +{added}건 추가")
    return items
