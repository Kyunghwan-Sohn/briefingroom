"""대통령실 보도자료 크롤러 (president.go.kr/newsroom/briefing)"""
from __future__ import annotations

import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

from briefingroom.config import HEADERS, DELAY

BASE = "https://www.president.go.kr"


def crawl_president(target: date) -> list[dict]:
    """대통령실 브리핑 수집"""
    print(f"\n[대통령실] {target} 보도자료 수집")
    s = requests.Session()
    s.headers.update(HEADERS)
    target_str = target.isoformat()
    all_items = []
    seen = set()

    url = f"{BASE}/newsroom/briefing"
    try:
        r = s.get(url, timeout=15)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}")
            return []

        soup = BeautifulSoup(r.text, "lxml")

        # 브리핑 항목 추출: 각 항목은 날짜 + 제목 + 링크
        for a in soup.select("a[href*='/newsroom/briefing/']"):
            text = a.get_text(separator="\n", strip=True)
            if not text or len(text) < 10:
                continue

            # 날짜 추출
            date_match = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", text)
            if not date_match:
                continue

            item_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            if item_date != target_str:
                continue

            href = a.get("href", "")
            if not href.startswith("http"):
                href = BASE + href

            # 제목 추출: 날짜 앞의 텍스트
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            # 첫 줄이 제목 (날짜는 보통 마지막)
            title = ""
            for line in lines:
                if re.match(r"\d{4}\.\d{2}\.\d{2}", line):
                    continue
                if not title:
                    title = line

            if not title or title in seen:
                continue
            seen.add(title)

            # 제목에서 본문 분리
            # "전군주요지휘관회의 개최 관련 강유정 대변인 서면 브리핑이재명 대통령은..."
            # → "관련" 이후 "브리핑" 까지가 제목
            briefing_idx = title.find("브리핑")
            if briefing_idx > 10 and briefing_idx < len(title) - 5:
                after = title[briefing_idx + len("브리핑"):]
                # 브리핑 뒤에 바로 본문이 시작되면 자르기
                if after and re.match(r'[가-힣]', after[0]):
                    title = title[:briefing_idx + len("브리핑")]

            # 최종 제목 정제
            title = re.sub(r"\s{2,}", " ", title).strip()
            if len(title) > 70:
                cut = title.rfind(" ", 0, 70)
                title = title[:cut].strip() if cut > 20 else title[:67] + "..."

            all_items.append({
                "source": "대통령실",
                "title": title,
                "url": href,
                "date": item_date,
                "pdfs": [],
                "hwps": [],
                "files": [],
                "text": "",
                "body_text": "",
                "summary": "",
            })

    except Exception as e:
        print(f"  [대통령실 오류] {e}")

    print(f"  -> 대통령실 총 {len(all_items)}건 수집 완료")
    return all_items
