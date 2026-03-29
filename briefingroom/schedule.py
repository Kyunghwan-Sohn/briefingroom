"""차주 정부 일정 크롤링 + 텔레그램 발송

소스:
  1. 이투데이 "정부 주요 일정" 기사 (etoday.co.kr)
  2. 머니투데이 "정부부처 주간일정 및 보도계획" 기사
  3. 대통령실 캘린더 (president.go.kr/president/calendar_day)

매주 일요일 오후 실행 → 텔레그램 + HTML 포스트.
"""
from __future__ import annotations

import html as _html
import re
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from briefingroom.config import BASE_DIR, HEADERS
from briefingroom.telegram import SITE_URL, _escape_html, send_telegram, TELEGRAM_ENABLED

ARTICLES_DIR = BASE_DIR / "articles"


# ═══════════════════════════════════════════════════════════
#  1. 대통령실 캘린더
# ═══════════════════════════════════════════════════════════

def crawl_president_schedule(start: date, end: date) -> list[dict]:
    """대통령실 공개일정 크롤링 (날짜별 페이지)"""
    items = []
    s = requests.Session()
    s.headers.update(HEADERS)

    d = start
    while d <= end:
        url = f"https://www.president.go.kr/president/calendar_day?date={d.isoformat()}"
        try:
            r = s.get(url, timeout=15)
            if r.status_code != 200:
                d += timedelta(days=1)
                continue

            soup = BeautifulSoup(r.text, "lxml")

            # 일정 텍스트 추출 — ul.txtList li
            for el in soup.select("ul.txtList li, div.txt_wrap li, div.open_schedule li"):
                text = el.get_text(strip=True)
                if not text or len(text) < 3 or "등록된 일정이 없습니다" in text:
                    continue

                # "HH:MM 행사명 / 장소" 패턴 파싱
                m = re.match(r"(\d{1,2}:\d{2})\s+(.+?)(?:\s*/\s*(.+))?$", text)
                if m:
                    items.append({
                        "date": d.isoformat(),
                        "dow": ["월", "화", "수", "목", "금", "토", "일"][d.weekday()],
                        "time": m.group(1),
                        "title": m.group(2).strip(),
                        "location": (m.group(3) or "").strip(),
                        "source": "대통령실",
                    })
                else:
                    items.append({
                        "date": d.isoformat(),
                        "dow": ["월", "화", "수", "목", "금", "토", "일"][d.weekday()],
                        "time": "",
                        "title": text[:100],
                        "location": "",
                        "source": "대통령실",
                    })

        except Exception as e:
            print(f"  [대통령실] {d} 크롤링 실패: {e}")

        d += timedelta(days=1)
        time.sleep(1)

    print(f"  [대통령실] {len(items)}건 수집 ({start} ~ {end})")
    return items


# ═══════════════════════════════════════════════════════════
#  2. 머니투데이 주간일정 기사
# ═══════════════════════════════════════════════════════════

def _find_mt_article_url() -> str | None:
    """Google News RSS로 최신 '정부부처 주간일정' 기사 URL 찾기"""
    from urllib.parse import quote
    import xml.etree.ElementTree as ET

    query = quote("정부부처 주간일정 보도계획")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"

    try:
        r = requests.get(rss_url, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.text)

        for item in root.findall(".//item"):
            title = (item.find("title").text or "").strip()
            source = item.find("source")
            source_name = source.text if source is not None else ""

            if "주간일정" in title:
                # Google News RSS의 description에서 원본 URL 추출
                desc = item.find("description")
                if desc is not None and desc.text:
                    soup = BeautifulSoup(desc.text, "lxml")
                    a = soup.find("a", href=True)
                    if a:
                        print(f"  [머니투데이] 기사 발견: {title[:50]}")
                        return a["href"]

                # description에 없으면 link에서 리다이렉트 따라가기
                link = (item.find("link").text or "").strip()
                if link:
                    try:
                        rr = requests.get(link, timeout=10, allow_redirects=True,
                                          headers={"User-Agent": "Mozilla/5.0"})
                        if rr.status_code == 200 and "mt.co.kr" in rr.url:
                            print(f"  [머니투데이] 기사 발견 (redirect): {title[:50]}")
                            return rr.url
                    except Exception:
                        pass

    except Exception as e:
        print(f"  [머니투데이] RSS 검색 실패: {e}")

    return None


def _fetch_article_body(url: str) -> str:
    """기사 URL에서 본문 텍스트 추출"""
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0"})
        r = s.get(url, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            return ""

        soup = BeautifulSoup(r.text, "lxml")

        # 기사 본문 셀렉터 (이투데이, 머니투데이, 일반 뉴스)
        for sel in ["div.articleView", "div#textBody", "div.article_body",
                     "div.view_cont", "div#article-view-content-div",
                     "div.newsct_article", "div#newsViewArea"]:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 200:
                return el.get_text(separator="\n", strip=True)

        return ""
    except Exception as e:
        print(f"  [기사] 본문 추출 실패: {e}")
        return ""


def _parse_mt_schedule(body: str, week_start: date) -> list[dict]:
    """머니투데이 본문 텍스트 → 구조화된 일정 리스트"""
    items = []
    current_dept = None
    current_day = None
    month = week_start.month

    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 부처 헤더: ◆기획재정부
        m = re.match(r"[◆◇■□▶]?\s*([가-힣]{2,15}(?:부|처|실|청|원|위원회|은행))\s*$", line)
        if m:
            current_dept = m.group(1).strip()
            current_day = None
            continue

        # 날짜 헤더: 7일(화) or 3월 7일(화)
        m = re.match(r"(?:(\d{1,2})월\s*)?(\d{1,2})일\(([월화수목금토일])\)", line)
        if m and current_dept:
            day = int(m.group(2))
            dow = m.group(3)
            # 날짜 계산
            try:
                d = date(week_start.year, month, day)
                current_day = d.isoformat()
            except ValueError:
                current_day = None
            continue

        # 일정 항목: *김윤상 2차관, 국무회의(오전 10시, 서울청사)
        m = re.match(r"[*·\-•]\s*(.+)", line)
        if m and current_dept and current_day:
            item_text = m.group(1).strip()
            if re.match(r"일정\s*없음", item_text):
                continue

            # 시간/장소 추출
            time_str = ""
            location = ""
            tm = re.search(r"\(([오전오후]+\s*\d{1,2}시(?:\d{1,2}분)?),?\s*(.+?)\)$", item_text)
            if tm:
                time_str = tm.group(1)
                location = tm.group(2)
                item_text = item_text[:tm.start()].strip().rstrip(",")

            items.append({
                "date": current_day,
                "dow": ["월", "화", "수", "목", "금", "토", "일"][
                    date.fromisoformat(current_day).weekday()],
                "time": time_str,
                "title": item_text[:100],
                "location": location,
                "source": current_dept,
            })

    print(f"  [머니투데이] {len(items)}건 파싱 ({len(set(i['source'] for i in items))}개 부처)")
    return items


def crawl_mt_schedule(week_start: date) -> list[dict]:
    """머니투데이 주간일정 기사 크롤링"""
    print("  [머니투데이] 기사 검색 중...")
    url = _find_mt_article_url()
    if not url:
        print("  [머니투데이] 기사 못 찾음")
        return []

    print(f"  [머니투데이] 본문 추출 중... {url[:60]}")
    body = _fetch_article_body(url)
    if not body:
        print("  [머니투데이] 본문 추출 실패")
        return []

    return _parse_mt_schedule(body, week_start)


# ═══════════════════════════════════════════════════════════
#  2-b. 이투데이 주간일정 기사
# ═══════════════════════════════════════════════════════════

def _find_etoday_url(week_start: date) -> str | None:
    """이투데이 '정부 주요 일정' 최신 기사 URL 검색"""
    try:
        r = requests.get(
            "https://www.etoday.co.kr/search/",
            params={"keyword": "정부 주요 일정 주간"},
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select("a[href*='/news/']"):
            title = a.get_text(strip=True)
            if ("주간 일정" in title or "주요 일정" in title) and (
                f"{week_start.month}월" in title
                or f"{week_start.day}일" in title
            ):
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.etoday.co.kr" + href
                print(f"  [이투데이] 기사 발견: {title[:50]}")
                return href

    except Exception as e:
        print(f"  [이투데이] 검색 실패: {e}")
    return None


def _parse_etoday_schedule(body: str, week_start: date) -> list[dict]:
    """이투데이 본문 → 구조화된 일정 (△ 마커 기반)"""
    items = []
    current_dept = None
    current_day = None
    month = week_start.month

    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 부처 헤더: ◇재정경제부, ◆국토교통부 등
        m = re.match(r"[◆◇■□▶●]?\s*([가-힣]{2,15}(?:부|처|실|청|원|위원회|은행|공사))\s*$", line)
        if m:
            current_dept = m.group(1).strip()
            current_day = None
            continue

        # 날짜 헤더: 30일(월), 1일(수), 3월 30일(월)
        m = re.match(r"(?:(\d{1,2})월\s*)?(\d{1,2})일\(([월화수목금토일])\)", line)
        if m:
            day = int(m.group(2))
            mon = int(m.group(1)) if m.group(1) else month
            # 월 넘김 처리: week_start가 3/30이고 day가 1~6이면 다음 달
            if not m.group(1) and day < week_start.day and day <= 7:
                mon = month + 1 if month < 12 else 1
            try:
                yr = week_start.year + (1 if mon < month else 0)
                d = date(yr, mon, day)
                current_day = d.isoformat()
            except ValueError:
                current_day = None
            continue

        # 일정 항목: △경제부총리 11:00 임시 국무회의(서울청사)
        m = re.match(r"[△▲*·\-•]\s*(.+)", line)
        if m and current_dept and current_day:
            item_text = m.group(1).strip()
            if re.match(r"일정\s*없음", item_text):
                continue

            # 시간 추출: "경제부총리 11:00 ..." 또는 "(오전 10시, ...)"
            time_str = ""
            location = ""

            # HH:MM 패턴
            tm = re.search(r"(\d{1,2}:\d{2})\s+", item_text)
            if tm:
                time_str = tm.group(1)

            # (장소) 패턴
            loc = re.search(r"\(([^)]+)\)\s*$", item_text)
            if loc:
                location = loc.group(1)
                item_text = item_text[:loc.start()].strip()

            items.append({
                "date": current_day,
                "dow": ["월", "화", "수", "목", "금", "토", "일"][
                    date.fromisoformat(current_day).weekday()],
                "time": time_str,
                "title": item_text[:100],
                "location": location,
                "source": current_dept,
            })

    print(f"  [이투데이] {len(items)}건 파싱 ({len(set(i['source'] for i in items))}개 부처)")
    return items


def crawl_etoday_schedule(week_start: date) -> list[dict]:
    """이투데이 주간일정 기사 크롤링"""
    print("  [이투데이] 기사 검색 중...")
    url = _find_etoday_url(week_start)
    if not url:
        print("  [이투데이] 기사 못 찾음")
        return []

    print(f"  [이투데이] 본문 추출 중... {url[:60]}")
    body = _fetch_article_body(url)
    if not body:
        print("  [이투데이] 본문 추출 실패")
        return []

    return _parse_etoday_schedule(body, week_start)


# ═══════════════════════════════════════════════════════════
#  3. 통합 + 포맷
# ═══════════════════════════════════════════════════════════

def collect_next_week_schedule(target: date) -> list[dict]:
    """차주 정부 일정 통합 수집"""
    # 차주 월~금
    next_monday = target + timedelta(days=(7 - target.weekday()))
    next_friday = next_monday + timedelta(days=4)

    print(f"\n{'═' * 60}")
    print(f"[차주 정부 일정 수집] {next_monday} ~ {next_friday}")

    all_items = []

    # 이투데이 (1순위)
    etoday = crawl_etoday_schedule(next_monday)
    all_items.extend(etoday)

    # 머니투데이 (2순위 보완 소스)
    mt = crawl_mt_schedule(next_monday)
    all_items.extend(mt)

    # 대통령실 (항상 병합)
    president = crawl_president_schedule(next_monday, next_friday)
    all_items.extend(president)

    # 날짜 범위 필터링 (차주 월~금만)
    start_str = next_monday.isoformat()
    end_str = next_friday.isoformat()
    all_items = [it for it in all_items if start_str <= it["date"] <= end_str]

    # 날짜순 정렬
    all_items.sort(key=lambda x: (x["date"], x["time"]))

    deduped = []
    seen = set()
    for item in all_items:
        key = (item["date"], item["source"], item["time"], item["title"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    print(f"  총 {len(deduped)}건 수집 완료 ({start_str} ~ {end_str})")
    return deduped


def format_schedule_telegram(items: list[dict], target: date) -> str:
    """텔레그램 메시지 포맷"""
    next_monday = target + timedelta(days=(7 - target.weekday()))
    next_friday = next_monday + timedelta(days=4)

    lines = [
        f"📅 <b>차주 정부 주요 일정</b>",
        f"  {next_monday.month}/{next_monday.day}({['월','화','수','목','금','토','일'][next_monday.weekday()]}) ~ "
        f"{next_friday.month}/{next_friday.day}({['월','화','수','목','금','토','일'][next_friday.weekday()]})",
        "",
    ]

    post_url = f"{SITE_URL}/articles/schedule/{target.isoformat()}/"

    if not items:
        lines.append("  일정 정보 없음")
        lines.append("")
        lines.append(f'🔗 <a href="{SITE_URL}">govbrief.kr</a>')
        return "\n".join(lines)

    # 날짜별 그룹핑
    by_date = defaultdict(list)
    for it in items:
        by_date[it["date"]].append(it)

    MAX_PER_DAY = 4  # 일자별 주요 일정 수
    # 필수 포함 부처 (대통령실 + 주요 경제부처)
    MUST_SOURCES = {"대통령실", "금융위원회", "국토교통부", "산업통상자원부",
                    "산업통상부", "국토부", "금융위"}

    for d in sorted(by_date.keys()):
        day_items = by_date[d]
        dt = date.fromisoformat(d)
        dow = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]

        lines.append(f"━━━ {dt.month}/{dt.day}({dow}) ━━━")

        # 우선순위: 대통령실 > 필수부처 > 시간 있는 일정 > 나머지
        must = []
        timed = []
        others = []
        seen = set()
        for it in day_items:
            if it["source"] in MUST_SOURCES:
                must.append(it)
            elif it["time"]:
                timed.append(it)
            else:
                others.append(it)

        # 필수부처 먼저 + 나머지로 채우기
        top_items = []
        for it in must + timed + others:
            key = it["title"][:30]
            if key not in seen:
                seen.add(key)
                top_items.append(it)
            if len(top_items) >= MAX_PER_DAY:
                break
        remaining = len(day_items) - len(top_items)

        for it in top_items:
            src = _escape_html(it["source"])
            raw_title = it["title"]
            time_str = it["time"] or ""
            loc = _escape_html(it["location"])

            # 제목에서 "부처명 차관/장관 HH:MM ..." 패턴 정리
            import re as _re
            # "산업부 차관 07:30 민주당 중동 특위" → "민주당 중동 특위"
            clean = _re.sub(r'^[\w가-힣]+\s+(장관|차관|[12]차관|본부장|위원장|청장|처장)\s*', '', raw_title)
            # 중복 시간 제거: "07:30 민주당..." 에서 시간 제거 (이미 time_str에 있음)
            clean = _re.sub(r'^\d{1,2}:\d{2}\s*', '', clean).strip()
            # 뒤에 붙은 다른 일정 제거 (여러 일정이 한 줄에 합쳐진 경우)
            # "임시 국무회의(서울청사) 14:00 한국노총 면담" → "임시 국무회의"
            multi = _re.search(r'\s+\d{1,2}:\d{2}\s+', clean)
            if multi:
                clean = clean[:multi.start()].strip()
            # 괄호 안 장소를 loc으로 이동
            loc_match = _re.search(r'\(([^)]+)\)\s*$', clean)
            if loc_match and not loc:
                loc = _escape_html(loc_match.group(1))
                clean = clean[:loc_match.start()].strip()

            title = _escape_html(clean)[:45]
            if not title:
                title = _escape_html(raw_title)[:45]

            # 포맷: 시간 | 부처 | 일정 (장소)
            time_part = f"{time_str} " if time_str else "종일 "
            loc_part = f" ({loc})" if loc else ""
            lines.append(f"  ▸ {time_part}<b>{src}</b> {title}{loc_part}")

        if remaining > 0:
            lines.append(f"  <i>... 외 {remaining}건</i>")

        lines.append("")

    lines.append("──────────────────")
    total = len(items)
    dept_count = len(set(it["source"] for it in items))
    lines.append(f"총 {total}건 · {dept_count}개 부처")
    lines.append(f'📄 <a href="{post_url}">전체 일정 보기</a>')

    return "\n".join(lines)


def generate_schedule_post(items: list[dict], target: date) -> str:
    """차주 일정 HTML 포스트 생성 — 카드 기반 비주얼 디자인"""
    next_monday = target + timedelta(days=(7 - target.weekday()))
    next_friday = next_monday + timedelta(days=4)
    post_url = f"{SITE_URL}/articles/schedule/{target.isoformat()}/"

    h = _html.escape
    dows = ["월", "화", "수", "목", "금", "토", "일"]
    day_colors = {"월": "#2f54eb", "화": "#16a34a", "수": "#d97706", "목": "#dc2626", "금": "#7c3aed"}

    # 날짜별 그룹
    by_date = defaultdict(list)
    for it in items:
        by_date[it["date"]].append(it)

    # 통계
    total = len(items)
    dept_count = len(set(it["source"] for it in items))
    dept_top = defaultdict(int)
    for it in items:
        dept_top[it["source"]] += 1
    top5 = sorted(dept_top.items(), key=lambda x: -x[1])[:5]

    # 날짜별 카드 HTML
    day_cards = ""
    for d in sorted(by_date.keys()):
        dt = date.fromisoformat(d)
        dow = dows[dt.weekday()]
        color = day_colors.get(dow, "#2f54eb")
        day_items = by_date[d]

        items_html = ""
        for it in day_items:
            time_str = h(it["time"]) if it["time"] else "종일"
            loc = h(it["location"])
            loc_html = f' <span style="color:#96938c;font-size:11px">({loc})</span>' if loc else ""
            items_html += f'''<div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #f0eeea">
  <div style="min-width:44px;font-family:'DM Mono',monospace;font-size:11px;color:{color};font-weight:600;padding-top:2px">{time_str}</div>
  <div style="flex:1;min-width:0">
    <div style="font-size:11px;font-weight:600;color:{color};margin-bottom:2px">{h(it["source"])}</div>
    <div style="font-size:13px;color:#1c1b18;word-break:keep-all">{h(it["title"])}{loc_html}</div>
  </div>
</div>'''

        day_cards += f'''<div style="margin-bottom:20px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
    <div style="width:48px;height:48px;background:{color};border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;flex-shrink:0">
      <span style="font-size:18px;font-weight:700;line-height:1">{dt.day}</span>
      <span style="font-size:10px;font-weight:600">{dow}요일</span>
    </div>
    <div>
      <div style="font-size:15px;font-weight:700;color:#1c1b18">{dt.month}월 {dt.day}일 ({dow})</div>
      <div style="font-size:12px;color:#96938c">{len(day_items)}건</div>
    </div>
  </div>
  <div style="background:#fff;border:1px solid #e0ddd7;border-radius:12px;padding:4px 16px;overflow:hidden">
    {items_html}
  </div>
</div>'''

    # 주요 부처 태그
    dept_tags = " ".join(
        f'<span style="font-size:11px;padding:4px 12px;border-radius:20px;background:#eef0fd;color:#2f54eb;border:1px solid rgba(47,84,235,.15)">{h(s)} {c}건</span>'
        for s, c in top5
    )

    page_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>정부 주요 일정 ({next_monday.month}/{next_monday.day}~{next_friday.month}/{next_friday.day}) - 브리핑룸</title>
<meta name="description" content="대한민국 정부 주요 일정 ({next_monday} ~ {next_friday}). 대통령실, 부처별 주간 계획, 국무회의 일정.">
<meta property="og:title" content="정부 주요 일정 ({next_monday.month}/{next_monday.day}~{next_friday.month}/{next_friday.day}) - 브리핑룸">
<meta property="og:description" content="총 {total}건 · {dept_count}개 부처 주요 일정">
<meta property="og:url" content="{post_url}">
<link rel="canonical" href="{post_url}">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&family=Pretendard:wght@400;600;700&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#f5f4f0;color:#1c1b18;font-family:'Pretendard',sans-serif;line-height:1.6}}
body::before{{content:'';position:fixed;inset:0;background-image:radial-gradient(circle at 1px 1px,#e0ddd7 1px,transparent 0);background-size:24px 24px;opacity:.4;pointer-events:none;z-index:0}}
.wrap{{max-width:720px;margin:0 auto;padding:32px 20px;position:relative;z-index:1}}
.back{{display:inline-flex;align-items:center;gap:6px;color:#96938c;text-decoration:none;font-size:12px;margin-bottom:20px;padding:7px 14px;background:#fff;border:1px solid #e0ddd7;border-radius:8px}}
.back:hover{{color:#1c1b18}}
.hero{{background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);border-radius:16px;padding:28px 24px;margin-bottom:24px;color:#fff}}
.hero h1{{font-family:'Noto Serif KR',serif;font-size:24px;font-weight:700;margin-bottom:6px;letter-spacing:-.5px}}
.hero .sub{{font-size:13px;color:rgba(255,255,255,.7);margin-bottom:16px}}
.stats{{display:flex;gap:10px;flex-wrap:wrap}}
.stat{{text-align:center;padding:10px 16px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);border-radius:10px;flex:1;min-width:80px}}
.stat-num{{font-family:'Noto Serif KR',serif;font-size:20px;font-weight:700}}
.stat-label{{font-size:10px;color:rgba(255,255,255,.6);margin-top:2px}}
.tags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:24px}}
.footer{{margin-top:32px;padding-top:16px;border-top:1px solid #e0ddd7;font-size:11px;color:#96938c;text-align:center}}
@media(max-width:768px){{.wrap{{padding:20px 16px}}.hero h1{{font-size:20px}}.hero{{padding:20px 16px}}}}
</style>
</head>
<body>
<div class="wrap">
<a class="back" href="/">← 브리핑룸으로</a>

<div class="hero">
  <h1>📅 정부 주요 일정</h1>
  <div class="sub">{next_monday.year}년 {next_monday.month}월 {next_monday.day}일({dows[next_monday.weekday()]}) ~ {next_friday.month}월 {next_friday.day}일({dows[next_friday.weekday()]})</div>
  <div class="stats">
    <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">총 일정</div></div>
    <div class="stat"><div class="stat-num">{dept_count}</div><div class="stat-label">부처</div></div>
    <div class="stat"><div class="stat-num">{len(by_date)}</div><div class="stat-label">일</div></div>
  </div>
</div>

<div class="tags">{dept_tags}</div>

{day_cards}

<div class="footer">
  govbrief.kr · 출처: 이투데이, 머니투데이, 대통령실 · {date.today().isoformat()}
</div>
</div>
</body>
</html>"""

    out_dir = ARTICLES_DIR / "schedule" / target.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(page_html, encoding="utf-8")
    print(f"  [HTML] {out_path}")
    return post_url


# ═══════════════════════════════════════════════════════════
#  4. 메인 실행
# ═══════════════════════════════════════════════════════════

def run_schedule(target: date) -> bool:
    """차주 정부 일정 전체 파이프라인"""
    print(f"\n{'═' * 60}")
    print("[차주 정부 일정 크롤링]")

    # 1. 수집
    items = collect_next_week_schedule(target)

    # 2. HTML 포스트
    print("  [포스트 생성]")
    post_url = generate_schedule_post(items, target)

    # 3. 텔레그램
    msg = format_schedule_telegram(items, target)
    print(f"  메시지 길이: {len(msg)}자")

    if TELEGRAM_ENABLED:
        send_telegram(msg)
    else:
        print("  [텔레그램] TELEGRAM_ENABLED=false -> 스킵")

    return True
