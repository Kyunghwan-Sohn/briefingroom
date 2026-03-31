"""정부 지원사업 통합 크롤러 + 텔레그램 발송

Tier 1 소스:
  1. 중소벤처기업부 (mss.go.kr) — 사업공고
  2. K-Startup (k-startup.go.kr) — 창업 지원사업
  3. NTIS (ntis.go.kr) — R&D 통합공고

매일 09:00 KST 실행 → 신규 공고 수집 → AI 요약 → 텔레그램 + 웹
"""
from __future__ import annotations

import html as _html
import re
import sqlite3
import ssl
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from briefingroom.config import BASE_DIR
from briefingroom.telegram import SITE_URL, _escape_html, send_telegram, TELEGRAM_ENABLED

SUBSIDY_DB = BASE_DIR / "subsidy.db"
ARTICLES_DIR = BASE_DIR / "articles"


# ═══════════════════════════════════════════════════════════
#  HTTP 세션
# ═══════════════════════════════════════════════════════════

class _TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def _session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    s.mount("https://", _TLSAdapter(max_retries=3))
    return s


# ═══════════════════════════════════════════════════════════
#  SQLite DB
# ═══════════════════════════════════════════════════════════

def _init_db():
    conn = sqlite3.connect(str(SUBSIDY_DB))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subsidies (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT,
            ministry TEXT,
            apply_start TEXT,
            apply_end TEXT,
            detail_url TEXT,
            summary TEXT,
            d_day INTEGER,
            status TEXT DEFAULT 'active',
            registered_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(source, title)
        );
        CREATE INDEX IF NOT EXISTS idx_sub_status ON subsidies(status);
        CREATE INDEX IF NOT EXISTS idx_sub_end ON subsidies(apply_end);
    """)
    conn.commit()
    conn.close()


def _is_new(source: str, title: str) -> bool:
    """이미 수집된 공고인지 확인"""
    conn = sqlite3.connect(str(SUBSIDY_DB))
    row = conn.execute(
        "SELECT 1 FROM subsidies WHERE source=? AND title=?",
        (source, title.strip()),
    ).fetchone()
    conn.close()
    return row is None


def _save(item: dict):
    conn = sqlite3.connect(str(SUBSIDY_DB))
    conn.execute("""
        INSERT OR IGNORE INTO subsidies
        (id, source, title, category, ministry, apply_start, apply_end,
         detail_url, summary, d_day, status, registered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.get("id", ""),
        item.get("source", ""),
        item.get("title", "").strip(),
        item.get("category", ""),
        item.get("ministry", ""),
        item.get("apply_start", ""),
        item.get("apply_end", ""),
        item.get("detail_url", ""),
        item.get("summary", ""),
        item.get("d_day", -1),
        "active",
        item.get("registered_at", ""),
    ))
    conn.commit()
    conn.close()


def _calc_dday(end_date: str) -> int:
    """마감일까지 D-day 계산"""
    try:
        if len(end_date) == 10:  # YYYY-MM-DD
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        elif len(end_date) == 8:  # YYYYMMDD
            end = datetime.strptime(end_date, "%Y%m%d").date()
        else:
            return -1
        return (end - date.today()).days
    except (ValueError, TypeError):
        return -1


# ═══════════════════════════════════════════════════════════
#  1. 중소벤처기업부 크롤러
# ═══════════════════════════════════════════════════════════

def crawl_mss() -> list[dict]:
    """중소벤처기업부 사업공고 크롤링"""
    print("  [중기부] 크롤링...")
    items = []
    s = _session()

    try:
        r = s.get("https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=310",
                  timeout=20)
        if r.status_code != 200:
            print(f"  [중기부] HTTP {r.status_code}")
            return []

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("table tbody tr")

        for row in rows:
            onclick = row.get("onclick", "")
            title_el = row.find("a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title:
                continue

            # onclick에서 ID 추출: doBbsFView('310','1066810',...)
            m = re.search(r"doBbsFView\('(\d+)','(\d+)'", onclick)
            cb_idx = m.group(1) if m else "310"
            bc_idx = m.group(2) if m else ""
            detail_url = f"https://www.mss.go.kr/site/smba/ex/bbs/View.do?cbIdx={cb_idx}&bcIdx={bc_idx}"

            tds = row.find_all("td")
            category = tds[0].get_text(strip=True) if len(tds) > 0 else ""
            period = ""
            d_day_text = ""
            for td in tds:
                text = td.get_text(strip=True)
                if "~" in text and ("20" in text or "접수" in text):
                    period = text
                if text.startswith("D-") or text == "마감":
                    d_day_text = text

            # 기간 파싱
            apply_start = ""
            apply_end = ""
            period_match = re.search(r"(\d{4}[.\-/]\d{2}[.\-/]\d{2})\s*~\s*(\d{4}[.\-/]\d{2}[.\-/]\d{2})", period)
            if period_match:
                apply_start = period_match.group(1).replace(".", "-").replace("/", "-")
                apply_end = period_match.group(2).replace(".", "-").replace("/", "-")

            d_day = _calc_dday(apply_end) if apply_end else -1

            if _is_new("mss", title):
                items.append({
                    "id": f"mss_{bc_idx}",
                    "source": "mss",
                    "title": title,
                    "category": category,
                    "ministry": "중소벤처기업부",
                    "apply_start": apply_start,
                    "apply_end": apply_end,
                    "detail_url": detail_url,
                    "d_day": d_day,
                    "registered_at": date.today().isoformat(),
                })

        print(f"  [중기부] {len(items)}건 신규")
    except Exception as e:
        print(f"  [중기부] 실패: {e}")

    time.sleep(1)
    return items


# ═══════════════════════════════════════════════════════════
#  2. K-Startup 크롤러
# ═══════════════════════════════════════════════════════════

def crawl_kstartup() -> list[dict]:
    """K-Startup 창업 지원사업 크롤링"""
    print("  [K-Startup] 크롤링...")
    items = []
    s = _session()

    try:
        r = s.get("https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do",
                  timeout=20)
        if r.status_code != 200:
            print(f"  [K-Startup] HTTP {r.status_code}")
            return []

        soup = BeautifulSoup(r.text, "lxml")
        wrap = soup.select_one("div.board_list-wrap")
        if not wrap:
            print("  [K-Startup] board_list-wrap 없음")
            return []

        lis = wrap.select("ul li")
        for li in lis:
            link = li.find("a", href=True)
            if not link:
                continue

            href = link.get("href", "")
            # javascript:go_view(176981) 에서 ID 추출
            m = re.search(r"go_view\((\d+)\)", href)
            if not m:
                continue
            pbanc_sn = m.group(1)

            title = link.get_text(strip=True)
            # "새로운게시글" 제거
            title = re.sub(r"새로운게시글$", "", title).strip()

            # 분야, D-day 추출
            spans = li.find_all("span")
            category = ""
            d_day_text = ""
            ministry = ""
            reg_date = ""
            for sp in spans:
                text = sp.get_text(strip=True)
                if text.startswith("D-") or text.startswith("D+"):
                    d_day_text = text
                elif re.match(r"^(글로벌|인력|사업화|창업교육|시설|R&D|멘토링|정책자금|판로|행사)", text):
                    category = text
                elif "등록일자" in text:
                    reg_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                    if reg_match:
                        reg_date = reg_match.group(1)
                elif len(text) > 2 and not text.startswith("20"):
                    ministry = text

            detail_url = f"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn={pbanc_sn}"
            d_day = int(d_day_text.replace("D-", "").replace("D+", "-")) if re.match(r"D[+-]\d+", d_day_text) else -1

            if _is_new("kstartup", title):
                items.append({
                    "id": f"kstartup_{pbanc_sn}",
                    "source": "kstartup",
                    "title": title,
                    "category": category,
                    "ministry": ministry or "창업진흥원",
                    "apply_start": "",
                    "apply_end": "",
                    "detail_url": detail_url,
                    "d_day": d_day,
                    "registered_at": reg_date or date.today().isoformat(),
                })

        print(f"  [K-Startup] {len(items)}건 신규")
    except Exception as e:
        print(f"  [K-Startup] 실패: {e}")

    time.sleep(1)
    return items


# ═══════════════════════════════════════════════════════════
#  3. NTIS R&D 통합공고 크롤러
# ═══════════════════════════════════════════════════════════

def crawl_ntis() -> list[dict]:
    """NTIS R&D 통합공고 크롤링"""
    print("  [NTIS] 크롤링...")
    items = []
    s = _session()

    try:
        r = s.post("https://www.ntis.go.kr/rndgate/eg/un/ra/list.do",
                   data={"pageIndex": 1, "recordCountPerPage": 30},
                   timeout=20)
        if r.status_code != 200:
            print(f"  [NTIS] HTTP {r.status_code}")
            return []

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("table tbody tr, li")

        for row in rows:
            link = row.find("a", href=True)
            if not link:
                continue

            href = link.get("href", "")
            if "view.do" not in href:
                continue

            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            # 상세 URL
            if href.startswith("/"):
                detail_url = f"https://www.ntis.go.kr{href}"
            else:
                detail_url = href

            # ID 추출
            uid_match = re.search(r"roRndUid=(\d+)", href)
            uid = uid_match.group(1) if uid_match else ""

            # 텍스트에서 부처명, 날짜 추출
            full_text = row.get_text(separator="|", strip=True)
            ministry = ""
            apply_start = ""
            apply_end = ""

            # 부처명 패턴
            for dept in ["과학기술정보통신부", "산업통상자원부", "보건복지부", "교육부",
                         "농림축산식품부", "국토교통부", "환경부", "해양수산부", "국방부",
                         "경찰청", "기획재정부", "고용노동부", "문화체육관광부"]:
                if dept in full_text:
                    ministry = dept
                    break

            # 날짜 패턴
            dates = re.findall(r"(\d{4}\.\d{2}\.\d{2})", full_text)
            if len(dates) >= 2:
                apply_start = dates[0].replace(".", "-")
                apply_end = dates[1].replace(".", "-")
            elif len(dates) == 1:
                apply_end = dates[0].replace(".", "-")

            d_day = _calc_dday(apply_end) if apply_end else -1

            # 현황 (접수중/접수예정/접수마감)
            status_text = ""
            tds = row.find_all("td") if row.name == "tr" else []
            for td in tds:
                text = td.get_text(strip=True)
                if text in ("접수중", "접수예정", "접수마감"):
                    status_text = text
                    break

            if status_text == "접수마감":
                continue

            if _is_new("ntis", title):
                items.append({
                    "id": f"ntis_{uid}",
                    "source": "ntis",
                    "title": title,
                    "category": "R&D",
                    "ministry": ministry,
                    "apply_start": apply_start,
                    "apply_end": apply_end,
                    "detail_url": detail_url,
                    "d_day": d_day,
                    "registered_at": date.today().isoformat(),
                })

        print(f"  [NTIS] {len(items)}건 신규")
    except Exception as e:
        print(f"  [NTIS] 실패: {e}")

    time.sleep(1)
    return items


# ═══════════════════════════════════════════════════════════
#  통합 + 텔레그램 + 웹
# ═══════════════════════════════════════════════════════════

def format_subsidy_telegram(items: list[dict]) -> str:
    """텔레그램 메시지 포맷"""
    if not items:
        return ""

    lines = [
        f"📢 <b>신규 정부 지원사업 ({len(items)}건)</b>",
        "",
    ]

    for item in items[:10]:  # 최대 10건
        title = _escape_html(item["title"])[:50]
        ministry = _escape_html(item.get("ministry", ""))
        category = _escape_html(item.get("category", ""))
        d_day = item.get("d_day", -1)
        url = item.get("detail_url", SITE_URL)

        d_day_str = f"D-{d_day}" if d_day >= 0 else "상시"
        cat_str = f"[{category}] " if category else ""

        lines.append(f"💰 {cat_str}<a href=\"{url}\">{title}</a>")
        lines.append(f"  {ministry} | {d_day_str}")
        lines.append("")

    lines.append("──────────────────")
    lines.append(f'📋 <a href="{SITE_URL}/subsidy/">전체 지원사업 보기</a>')

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3950] + f'\n\n... <a href="{SITE_URL}/subsidy/">더보기</a>'
    return text


def run_subsidy() -> bool:
    """지원사업 수집 전체 파이프라인"""
    print(f"\n{'═' * 60}")
    print("[정부 지원사업 수집]")

    _init_db()

    all_items = []

    # Tier 1 크롤링
    all_items.extend(crawl_mss())
    all_items.extend(crawl_kstartup())
    all_items.extend(crawl_ntis())

    print(f"\n  총 {len(all_items)}건 신규 수집")

    # DB 저장
    for item in all_items:
        _save(item)

    # 텔레그램 발송
    if all_items and TELEGRAM_ENABLED:
        msg = format_subsidy_telegram(all_items)
        if msg:
            print("  [텔레그램] 지원사업 알림 발송...")
            send_telegram(msg)
    elif not all_items:
        print("  신규 공고 없음 → 텔레그램 스킵")
    else:
        print("  [텔레그램] TELEGRAM_ENABLED=false → 스킵")

    return True
