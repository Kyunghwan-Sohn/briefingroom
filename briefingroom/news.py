"""관련 뉴스 기사 검색 + 요약

Google News RSS로 보도자료 관련 기사를 검색하고,
메이저 언론사 기사를 요약하여 WP 포스트에 추가합니다.
"""
from __future__ import annotations

import re
import ssl
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


# 메이저 언론사 (우선순위순)
MAJOR_MEDIA = {
    # 통신사
    "연합뉴스": "yna.co.kr",
    "뉴시스": "newsis.com",
    # 경제지
    "한국경제": "hankyung.com",
    "매일경제": "mk.co.kr",
    "서울경제": "sedaily.com",
    # 종합일간지
    "조선일보": "chosun.com",
    "중앙일보": "joongang.co.kr",
    "동아일보": "donga.com",
    "한겨레": "hani.co.kr",
    "경향신문": "khan.co.kr",
    # 방송
    "KBS": "kbs.co.kr",
    "MBC": "imnews.imbc.com",
    "SBS": "sbs.co.kr",
    "YTN": "ytn.co.kr",
}

MAJOR_NAMES = set(MAJOR_MEDIA.keys())


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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    s.mount("https://", _TLSAdapter(max_retries=2))
    return s


def search_related_news(title: str, source: str, max_results: int = 3) -> list[dict]:
    """Google News RSS로 관련 기사 검색, 메이저 언론사 우선"""
    # 검색 키워드: 부처명 + 제목 핵심어 (너무 길면 잘라냄)
    keywords = f"{source} {title[:40]}"
    query = quote(keywords)
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"

    try:
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
    except Exception:
        return []

    # 모든 기사 수집
    all_articles = []
    for item in root.findall(".//item"):
        news_title = item.find("title").text or ""
        news_source = item.find("source").text if item.find("source") is not None else ""
        news_link = item.find("link").text or ""
        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""

        # 원본 URL 추출 (Google 리다이렉트 URL에서)
        all_articles.append({
            "title": news_title.replace(f" - {news_source}", "").strip(),
            "source": news_source,
            "link": news_link,
            "pub_date": pub_date,
            "is_major": news_source in MAJOR_NAMES,
        })

    # 메이저 언론사 우선 정렬
    major = [a for a in all_articles if a["is_major"]]
    others = [a for a in all_articles if not a["is_major"]]
    sorted_articles = major + others

    return sorted_articles[:max_results]


def fetch_article_text(url: str) -> str:
    """기사 원문 텍스트 추출 (요약용)"""
    s = _session()
    try:
        # Google News 리다이렉트 따라가기
        r = s.get(url, timeout=10, allow_redirects=True)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "lxml")

        # 공통 기사 본문 선택자
        for sel in [
            "article", "div#articleBodyContents", "div.article_body",
            "div#newsct_article", "div.news_body", "div#articeBody",
            "div.article-body", "div.article_txt", "div#article-view-content-div",
            "div.content_text", "div#textBody", "div.view_cont",
        ]:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 100:
                text = re.sub(r"\s+", " ", el.get_text(strip=True))
                return text[:2000]

        # 폴백: og:description
        og = soup.find("meta", property="og:description")
        if og and og.get("content") and len(og["content"]) > 30:
            return og["content"][:500]

        return ""
    except Exception:
        return ""


def get_news_for_item(item: dict, llm_fn=None) -> list[dict]:
    """보도자료 1건에 대한 관련 뉴스 기사 검색 + 요약"""
    articles = search_related_news(item["title"], item["source"])

    enriched = []
    for art in articles:
        # Google News에서 og:description으로 짧은 요약 추출
        text = fetch_article_text(art["link"])

        # LLM 요약 (함수가 전달된 경우)
        news_summary = ""
        if llm_fn and text and len(text) > 50:
            try:
                result = llm_fn({
                    "source": art["source"],
                    "title": art["title"],
                    "text": text[:1500],
                })
                if not result.startswith("["):
                    # "요약:" 접두사 제거
                    news_summary = result.replace("요약:", "").split("키워드:")[0].strip()
                    if len(news_summary) > 200:
                        news_summary = news_summary[:197] + "..."
            except Exception:
                pass

        # LLM 실패 시 본문 앞부분 사용
        if not news_summary and text:
            news_summary = text[:150] + "..." if len(text) > 150 else text

        enriched.append({
            "title": art["title"],
            "source": art["source"],
            "link": art["link"],
            "summary": news_summary,
            "is_major": art["is_major"],
        })
        time.sleep(0.3)

    return enriched


def format_news_html(articles: list[dict]) -> str:
    """관련 뉴스를 WP 포스트용 HTML로 포맷 — 요약 + 링크 분리"""
    if not articles:
        return ""

    rows = ""
    for art in articles:
        badge_color = "#2f54eb" if art["is_major"] else "#96938c"
        summary = art.get("summary", "")
        summary_html = f'<p style="font-size:12px;color:#4a4844;line-height:1.5;margin:4px 0 0 0">{summary}</p>' if summary else ""

        rows += f"""
    <div style="padding:10px 0;border-bottom:1px solid #e0ddd7">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:2px">
        <span style="background:{badge_color}18;color:{badge_color};font-size:10px;padding:2px 8px;border-radius:4px;font-family:monospace;white-space:nowrap;flex-shrink:0">{art['source']}</span>
        <span style="font-size:13px;font-weight:500;color:#1c1b18;line-height:1.4">{art['title'][:70]}</span>
      </div>
      {summary_html}
      <a href="{art['link']}" target="_blank" style="display:inline-block;margin-top:4px;font-family:monospace;font-size:11px;color:#2f54eb;text-decoration:none">↗ 기사 원문 보기</a>
    </div>"""

    return f"""
  <div class="briefing-news" style="margin-top:16px">
    <h4 style="font-family:'Noto Serif KR',serif;font-size:14px;font-weight:600;color:#1c1b18;margin:0 0 8px;display:flex;align-items:center;gap:6px">
      📰 관련 뉴스 기사
    </h4>
    {rows}
  </div>"""
