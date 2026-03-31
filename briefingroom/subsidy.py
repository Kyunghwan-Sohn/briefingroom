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
from briefingroom.site_templates import SITE_NAV_CSS, render_crosslinks, render_top_nav
from briefingroom.telegram import SITE_URL, _escape_html, send_telegram, TELEGRAM_ENABLED

SUBSIDY_DB = BASE_DIR / "subsidy.db"
ARTICLES_DIR = BASE_DIR / "articles"

KNOWN_SUBSIDY_CATEGORIES = {
    "R&D",
    "사업화",
    "정책자금",
    "글로벌",
    "인력",
    "창업교육",
    "시설",
    "판로",
    "행사",
    "멘토링",
    "멘토링ㆍ컨설팅ㆍ교육",
}


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


def _normalize_subsidy_category(raw: str) -> str:
    category = (raw or "").strip()
    if not category:
        return "기타"
    if re.fullmatch(r"\d{4,}", category):
        return "기타"
    if category in KNOWN_SUBSIDY_CATEGORIES:
        return category
    if "멘토링" in category or "컨설팅" in category or "교육" in category:
        return "멘토링ㆍ컨설팅ㆍ교육" if "컨설팅" in category else "창업교육"
    return category


def _safe_detail_url(url: str) -> str:
    value = str(url or "").strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return ""


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
                    category = _normalize_subsidy_category(text)
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
                    "category": category or "기타",
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

    # JSON 내보내기 (웹사이트용)
    _export_json()

    # HTML 페이지 생성
    _generate_subsidy_page()

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


def _export_json():
    """활성 지원사업을 JSON으로 내보내기"""
    import json
    conn = sqlite3.connect(str(SUBSIDY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM subsidies WHERE status='active'
        ORDER BY apply_end ASC, created_at DESC
    """).fetchall()
    conn.close()

    items = []
    for r in rows:
        d_day = _calc_dday(r["apply_end"]) if r["apply_end"] else -1
        if d_day < -7:  # 마감 7일 이상 지난 건은 제외
            continue
        items.append({
            "id": r["id"],
            "source": r["source"],
            "title": r["title"],
            "category": r["category"],
            "ministry": r["ministry"],
            "apply_start": r["apply_start"],
            "apply_end": r["apply_end"],
            "detail_url": _safe_detail_url(r["detail_url"]),
            "d_day": d_day,
            "registered_at": r["registered_at"],
        })

    out = BASE_DIR / "data" / "subsidies.json"
    out.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "count": len(items),
        "items": items,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [JSON] {out.name}: {len(items)}건")


def _generate_subsidy_page():
    """지원사업 전용 정적 HTML 페이지 생성"""
    import json

    json_path = BASE_DIR / "data" / "subsidies.json"
    if not json_path.exists():
        return

    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])

    # 분야별 카운트
    cats = {}
    for it in items:
        c = it.get("category", "기타") or "기타"
        cats[c] = cats.get(c, 0) + 1

    # 마감 임박 (D-14 이내)
    urgent = [it for it in items if 0 <= it.get("d_day", -1) <= 14]

    h = _html.escape

    # 카드 HTML 생성
    def card(it):
        title = h(it["title"])[:55]
        ministry = h(it.get("ministry", ""))
        category = h(_normalize_subsidy_category(it.get("category", "")))
        d_day = it.get("d_day", -1)
        url = h(_safe_detail_url(it.get("detail_url", "")))
        end = it.get("apply_end", "")

        d_class = "urgent" if 0 <= d_day <= 7 else ("soon" if 0 <= d_day <= 14 else "")
        d_text = f"D-{d_day}" if d_day >= 0 else ("마감" if d_day < -1 else "상시")

        link_attr = f' href="{url}" target="_blank" rel="noopener noreferrer"' if url else ' href="#" aria-disabled="true" tabindex="-1"'
        return f"""<div class="sub-card" data-cat="{category or '기타'}">
          <div class="sub-card-top">
            <span class="sub-cat">{category}</span>
            <span class="sub-dday {d_class}">{d_text}</span>
          </div>
          <a class="sub-title"{link_attr}>{title}</a>
          <div class="sub-meta">{ministry}{(' | 마감 ' + end) if end else ''}</div>
        </div>"""

    cards_html = "\n".join(card(it) for it in items)

    # 분야 탭
    cat_tabs = '<button class="sub-tab active" onclick="subFilter(\'all\',this)">전체 ' + str(len(items)) + '</button>'
    for c, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        cat_tabs += f'<button class="sub-tab" onclick="subFilter(\'{h(c)}\',this)">{h(c)} {cnt}</button>'

    page_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>정부 지원사업 - 브리핑룸</title>
<meta name="description" content="중소벤처기업부, K-Startup, NTIS 등 정부 지원사업 공고를 매일 수집합니다.">
<link rel="canonical" href="{SITE_URL}/subsidy/">
<meta property="og:title" content="정부 지원사업 - 브리핑룸">
<meta property="og:description" content="정부 지원사업 공고를 매일 모아 마감일 중심으로 확인하세요.">
<meta property="og:url" content="{SITE_URL}/subsidy/">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@500;700&display=swap" rel="stylesheet">
<style>
:root{{--navy:#1a1a2e;--gold:#c9a84c;--bg:#f7f7f5;--surface:#fff;--border:#e0ddd7;--text:#1c1b18;--text2:#4a4844;--muted:#96938c}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Pretendard',sans-serif;min-height:100vh}}
.wrap{{max-width:900px;margin:0 auto;padding:24px 16px 80px}}
{SITE_NAV_CSS}
.hero{{background:linear-gradient(135deg,#1a1a2e,#2d2d4a);color:#fff;border-radius:16px;padding:20px;margin-bottom:20px}}
.hero-kicker{{font-size:11px;letter-spacing:.08em;color:rgba(255,255,255,.7);text-transform:uppercase;margin-bottom:8px}}
.hero-copy{{font-size:14px;line-height:1.6;color:rgba(255,255,255,.82);max-width:680px}}
.hero-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}}
.hero-btn{{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 14px;border-radius:10px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(255,255,255,.18)}}
.hero-btn.primary{{background:var(--gold);color:var(--navy);border-color:var(--gold)}}
.hero-btn.secondary{{background:rgba(255,255,255,.08);color:#fff}}
.back{{color:var(--muted);text-decoration:none;font-size:13px;display:inline-block;margin-bottom:20px}}
h1{{font-family:'Noto Serif KR',serif;font-size:26px;font-weight:700;margin-bottom:6px}}
.desc{{color:var(--text2);font-size:14px;margin-bottom:20px}}
.kpi-row{{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}}
.kpi{{flex:1;min-width:100px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center}}
.kpi-val{{font-size:22px;font-weight:700;color:var(--navy)}}
.kpi-label{{font-size:11px;color:var(--muted);margin-top:2px}}
.sub-tabs{{display:flex;gap:6px;overflow-x:auto;margin-bottom:16px;padding-bottom:4px}}
.sub-tab{{padding:6px 14px;border-radius:20px;border:1px solid var(--border);background:var(--surface);font-size:12px;cursor:pointer;white-space:nowrap;font-family:'Pretendard',sans-serif}}
.sub-tab.active{{background:var(--navy);color:#fff;border-color:var(--navy)}}
.sub-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.sub-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;transition:box-shadow .15s}}
.sub-card:hover{{box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.sub-card-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.sub-cat{{font-size:11px;padding:3px 8px;border-radius:4px;background:#eef0fd;color:var(--navy);font-weight:600}}
.sub-dday{{font-size:12px;font-weight:700;color:var(--navy)}}
.sub-dday.urgent{{color:#dc2626}}
.sub-dday.soon{{color:#d97706}}
.sub-title{{font-size:14px;font-weight:600;color:var(--text);text-decoration:none;display:block;line-height:1.5;margin-bottom:6px;min-height:44px}}
.sub-title:hover{{color:var(--navy);text-decoration:underline}}
.sub-title[aria-disabled="true"]{{color:var(--muted);pointer-events:none;text-decoration:none}}
.sub-meta{{font-size:11px;color:var(--muted)}}
.section-title{{font-family:'Noto Serif KR',serif;font-size:16px;font-weight:700;margin:24px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--border)}}
@media(max-width:600px){{.sub-grid{{grid-template-columns:1fr}}.kpi-row{{gap:8px}}.kpi{{padding:10px}}.hero{{padding:16px}}.hero-actions{{flex-direction:column}}.hero-btn{{width:100%}}}}
</style>
</head>
<body>
<div class="wrap">
{render_top_nav("subsidy")}
<a class="back" href="/">← 브리핑룸으로</a>
{render_crosslinks((f"{SITE_URL}/articles/weekly/", "주간 리포트"), (f"{SITE_URL}/articles/schedule/", "차주 일정"))}
<section class="hero" aria-label="지원사업 안내">
  <div class="hero-kicker">GovBrief Subsidy Radar</div>
  <h1>정부 지원사업</h1>
  <div class="hero-copy">마감일 임박 공고를 먼저 보여주고, 원문 공고로 바로 이동할 수 있게 정리했습니다. 텔레그램 채널과 메인 브리핑을 함께 보면 정책 발표와 지원사업을 같은 흐름에서 추적할 수 있습니다.</div>
  <div class="hero-actions">
    <a class="hero-btn primary" href="https://t.me/govbriefkr" target="_blank" rel="noopener noreferrer">텔레그램 채널</a>
    <a class="hero-btn secondary" href="/">보도자료 메인으로</a>
  </div>
</section>
<div class="desc">중소벤처기업부 · K-Startup · NTIS에서 매일 수집 | {data.get('generated_at','')[:10]}</div>

<div class="kpi-row">
  <div class="kpi"><div class="kpi-val">{len(items)}</div><div class="kpi-label">진행 중</div></div>
  <div class="kpi"><div class="kpi-val">{len(urgent)}</div><div class="kpi-label">마감 임박 (2주 이내)</div></div>
  <div class="kpi"><div class="kpi-val">{len(cats)}</div><div class="kpi-label">분야</div></div>
</div>

{'<div class="section-title">🔥 마감 임박</div><div class="sub-grid">' + "".join(card(it) for it in urgent) + '</div>' if urgent else ''}

<div class="section-title">전체 지원사업</div>
<div class="sub-tabs">{cat_tabs}</div>
<div class="sub-grid" id="sub-list">{cards_html}</div>
</div>

<script>
function subFilter(cat, el) {{
  document.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.sub-card').forEach(c => {{
    c.style.display = (cat === 'all' || c.dataset.cat === cat) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

    # 루트 /subsidy/ 경로에 생성 (GitHub Pages용)
    out_dir = BASE_DIR / "subsidy"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page_html, encoding="utf-8")
    # articles/subsidy/에도 복사 (하위 호환)
    art_dir = ARTICLES_DIR / "subsidy"
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "index.html").write_text(page_html, encoding="utf-8")
    print(f"  [HTML] subsidy/index.html 생성 ({len(items)}건)")
