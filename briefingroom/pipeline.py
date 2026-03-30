from __future__ import annotations

import re
import time

from briefingroom.crawlers.common import new_session
from briefingroom.files import download_file, extract_hwp, extract_pdf, save_text


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
        print(f"    ⚠ 텍스트 추출 실패 (PDF:{len(item['pdfs'])} HWP:{len(item['hwps'])})")
