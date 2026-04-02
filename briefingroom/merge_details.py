"""detail.html의 상세 브리핑 내용을 index.html에 합치기

detail.html의 핵심 요약, 왜 중요한가, 주요 내용, 시행 일정 등을
index.html의 요약 섹션 뒤에 삽입합니다.

실행: python -m briefingroom.merge_details
"""
import os
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "articles"


def extract_detail_content(detail_path: Path) -> str:
    """detail.html에서 상세 섹션 내용 추출"""
    text = detail_path.read_text(encoding="utf-8")

    # <div class="section"> ... </div> 블록 추출
    m = re.search(r'<div class="section">(.*?)</div>\s*<div style="margin-top', text, re.DOTALL)
    if not m:
        m = re.search(r'<div class="section">(.*?)</div>\s*</div>', text, re.DOTALL)
    if not m:
        return ""

    content = m.group(1).strip()
    if not content:
        return ""

    # info-section 형태로 감싸기
    sections = []
    parts = re.split(r'<h2>(.*?)</h2>', content)
    # parts[0]은 h2 이전 텍스트, 이후는 (제목, 내용) 쌍
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if not body:
            continue

        css_class = "info-section"
        if "중요" in title:
            css_class = "info-section why-box"
        elif "영향" in title or "시행" in title:
            css_class = "info-section impact-box"

        sections.append(
            f'<section class="{css_class}">\n'
            f'  <h3>{title}</h3>\n'
            f'  {body}\n'
            f'</section>'
        )

    return "\n    ".join(sections)


def merge():
    merged = 0
    skipped = 0

    for date_dir in sorted(BASE.iterdir()):
        if not date_dir.is_dir() or not date_dir.name.startswith("2026"):
            continue
        for art_dir in sorted(date_dir.iterdir()):
            if not art_dir.is_dir():
                continue

            index_path = art_dir / "index.html"
            detail_path = art_dir / "detail.html"

            if not index_path.exists() or not detail_path.exists():
                continue

            index_text = index_path.read_text(encoding="utf-8")

            # 이미 합쳐진 경우 스킵
            if "왜 중요한가" in index_text or "주요 내용" in index_text:
                skipped += 1
                continue

            detail_content = extract_detail_content(detail_path)
            if not detail_content:
                skipped += 1
                continue

            # 키워드 div 바로 앞에 삽입 (요약 뒤)
            insert_point = "    <div class='keywords'>"
            if insert_point not in index_text:
                # 대체 삽입점: </section> 뒤, links 앞
                insert_point = '<div class="links">'
                if insert_point not in index_text:
                    skipped += 1
                    continue

            new_text = index_text.replace(
                insert_point,
                f"    {detail_content}\n\n    {insert_point}",
                1,
            )

            index_path.write_text(new_text, encoding="utf-8")
            merged += 1

    print(f"[merge] 완료: {merged}건 합침, {skipped}건 스킵")


if __name__ == "__main__":
    merge()
