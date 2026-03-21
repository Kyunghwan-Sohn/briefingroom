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
    texts = []

    for i, url in enumerate(item["pdfs"], 1):
        fname = f"{item['date']}_{src}_{safe}_{i}.pdf"
        path = download_file(url, fname, s)
        if not path:
            continue
        text = extract_pdf(path)
        if text:
            item["files"].append(str(path))
            texts.append(text)
        time.sleep(0.3)

    if not texts and item["hwps"]:
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
            texts.append(text)
        time.sleep(0.3)

    if texts:
        item["text"] = "\n\n".join(texts)
        save_text(item, item["text"])

    if not item["text"]:
        print(f"    ⚠ 텍스트 추출 실패 (PDF:{len(item['pdfs'])} HWP:{len(item['hwps'])})")
