from __future__ import annotations

import re
import time

from bs4 import BeautifulSoup

from briefingroom.crawlers.common import new_session
from briefingroom.files import download_file, extract_hwp, extract_pdf, save_text


def _fetch_body_from_url(url: str, session) -> str:
    """원문 URL에서 HTML 본문 텍스트를 추출한다."""
    if not url or not url.startswith("http"):
        return ""
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return ""
        r.encoding = r.apparent_encoding or "utf-8"
        soup = BeautifulSoup(r.text, "lxml")

        # 불필요한 태그 제거
        for tag in soup.find_all(["script", "style", "nav", "footer", "iframe"]):
            tag.decompose()

        # 본문 영역 셀렉터 (한국 정부 사이트 공통)
        for sel in [
            "div.view_cont", "div.article_view", "div.detailCont",
            "div#contentView", "div.content_view", "div.bbs_detail",
            "div.view_con", "div.boardView", "div.board_view",
            "div.view-body", "div.view_body", "div.data_view",
            "article", "div.content", "main",
        ]:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 50:
                return re.sub(r"\s+", " ", el.get_text(strip=True))[:6000]

        # og:description 폴백
        og = soup.find("meta", property="og:description")
        if og and og.get("content") and len(og["content"]) > 30:
            return og["content"]
    except Exception as e:
        print(f"    [원문 추출 실패] {e}")
    return ""


def process_item(item):
    print(f"\n[{item['source']}] {item['title'][:70]}")
    s = new_session()
    src = re.sub(r"[^\w가-힣]", "", item["source"])[:4]
    safe = re.sub(r"[^\w가-힣]", "_", item["title"])[:30]

    # 본문 텍스트가 충분하면 파일 추출 생략
    body_text = item.get("body_text", "")
    if body_text and len(body_text) >= 200:
        print(f"    본문 텍스트 사용 ({len(body_text)}자)")
        item["text"] = body_text
        save_text(item, body_text)
        return

    # 본문 부족 → 첨부파일에서 추출
    file_texts = []

    # PDF 전부 열기
    for i, url in enumerate(item["pdfs"], 1):
        fname = f"{item['date']}_{src}_{safe}_{i}.pdf"
        path = download_file(url, fname, s)
        if not path:
            continue
        text = extract_pdf(path)
        if text:
            item["files"].append(str(path))
            file_texts.append(text)
        time.sleep(0.3)

    # PDF에서 텍스트를 못 얻었으면 HWP 전부 열기
    if not file_texts and item["hwps"]:
        print("    PDF 없음 → HWP 시도")
        for j, url in enumerate(item["hwps"], 1):
            ext = "hwpx" if "hwpx" in url.lower() else "hwp"
            fname = f"{item['date']}_{src}_{safe}_{j}.{ext}"
            path = download_file(url, fname, s)
            if not path:
                continue
            text = extract_hwp(path)
            if text:
                item["files"].append(str(path))
                file_texts.append(text)
            time.sleep(0.3)

    if file_texts:
        item["text"] = "\n\n".join(file_texts)
        save_text(item, item["text"])
    elif body_text:
        # 파일 추출 실패했지만 짧은 본문이라도 있으면 사용
        print(f"    파일 추출 실패 → 짧은 본문 사용 ({len(body_text)}자)")
        item["text"] = body_text
    elif not item.get("text"):
        # 최종 폴백: 원문 URL에서 직접 본문 추출 시도
        print(f"    ⚠ 파일 추출 실패 → 원문 URL 본문 추출 시도")
        fallback_text = _fetch_body_from_url(item.get("url", ""), s)
        if fallback_text and len(fallback_text) > 30:
            print(f"    원문 URL에서 본문 추출 성공 ({len(fallback_text)}자)")
            item["text"] = fallback_text
            item["body_text"] = fallback_text
        else:
            print(f"    ⚠ 텍스트 추출 실패 (PDF:{len(item['pdfs'])} HWP:{len(item['hwps'])})")
