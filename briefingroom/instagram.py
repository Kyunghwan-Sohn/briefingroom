"""Instagram Graph API 자동 포스팅

비즈니스 계정 + Facebook 페이지 연결이 필요하다.
캐러셀(여러 장) 포스팅을 지원한다.

필수 환경변수:
  INSTAGRAM_ACCESS_TOKEN  - 장기 액세스 토큰
  INSTAGRAM_ACCOUNT_ID    - Instagram 비즈니스 계정 ID
  INSTAGRAM_IMAGE_HOST    - 이미지 호스팅 베이스 URL (Graph API가 URL로 이미지를 가져감)
  INSTAGRAM_ENABLED       - true/false (기본값 false)
"""
from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import requests

from briefingroom.config import CAT_MAP

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
INSTAGRAM_IMAGE_HOST = os.environ.get("INSTAGRAM_IMAGE_HOST", "").rstrip("/")
INSTAGRAM_ENABLED = os.environ.get("INSTAGRAM_ENABLED", "false").lower() in ("true", "1", "yes")

GRAPH_API = "https://graph.facebook.com/v21.0"
SITE_URL = "https://govbrief.kr"

CAT_EMOJI = {
    "금융경제": "💰",
    "사회복지": "🏥",
    "산업기술": "⚙️",
    "외교안보": "🌏",
    "행정법제": "📜",
}

DAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]


def _build_caption(item: dict, target_date: date | str,
                   content: dict | None = None) -> str:
    """게시물 캡션 자동 생성 (출처 + 요약 + 해시태그)"""
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    source = item.get("source", "")
    title = item.get("title", "")
    summary = item.get("summary", "")
    url = item.get("url", "")
    category = item.get("category", CAT_MAP.get(source, ""))
    cat_emoji = CAT_EMOJI.get(category, "📋")
    day_ko = DAYS_KO[target_date.weekday()]

    # content가 있으면 LLM 생성 해시태그 우선 사용
    if content and content.get("hashtags"):
        tags = content["hashtags"]
    else:
        tags = item.get("keywords", [])[:4]
    hashtags = []
    for kw in tags:
        tag = kw.replace(" ", "").replace("-", "").replace("·", "")
        if tag:
            hashtags.append(f"#{tag}")
    if "#정책브리핑" not in hashtags:
        hashtags.append("#정책브리핑")
    hashtag_str = " ".join(hashtags[:5])

    # impact_line이 있으면 추가
    impact_line = ""
    if content and content.get("impact_line"):
        impact_line = f"\n💡 {content['impact_line']}\n"

    caption = (
        f"{cat_emoji} {source}\n"
        f"📋 {title}\n"
        f"\n"
        f"{summary}\n"
        f"{impact_line}\n"
        f"📅 {target_date.isoformat()} ({day_ko})\n"
        f"🔗 원문: {url}\n" if url else ""
        f"👉 더 많은 정책 브리핑은 프로필 링크에서\n"
        f"\n"
        f"{hashtag_str}"
    )
    return caption


def post_carousel(
    image_urls: list[str],
    caption: str,
) -> dict | None:
    """Instagram Graph API로 캐러셀 포스트를 발행한다.

    Args:
        image_urls: 공개 접근 가능한 이미지 URL 리스트 (2~10장)
        caption: 게시물 캡션

    Returns:
        성공 시 {"id": "...", "status": "ok"}, 실패 시 None
    """
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("  [Instagram] 인증 정보 없음 → 스킵")
        return None

    if len(image_urls) < 2:
        print("  [Instagram] 캐러셀은 2장 이상 필요")
        return None

    headers = {"Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}"}

    # Step 1: 개별 이미지 컨테이너 생성
    children_ids = []
    for url in image_urls:
        resp = requests.post(
            f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media",
            data={
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"  [Instagram] 이미지 컨테이너 실패: {resp.text[:100]}")
            return None
        container_id = resp.json().get("id")
        if not container_id:
            print(f"  [Instagram] 컨테이너 ID 없음: {resp.text[:100]}")
            return None
        children_ids.append(container_id)
        time.sleep(1)

    # Step 2: 캐러셀 컨테이너 생성
    resp = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  [Instagram] 캐러셀 컨테이너 실패: {resp.text[:100]}")
        return None
    carousel_id = resp.json().get("id")

    # Step 3: 게시 (Publish)
    # 컨테이너 준비 대기
    time.sleep(5)
    resp = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media_publish",
        data={
            "creation_id": carousel_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  [Instagram] 게시 실패: {resp.text[:100]}")
        return None

    post_id = resp.json().get("id", "")
    print(f"  [Instagram] 게시 완료: {post_id}")
    return {"id": post_id, "status": "ok"}


def post_daily_carousels(carousel_results: list[dict], target: date | str) -> list[dict]:
    """generate_daily_carousels 결과를 받아 Instagram에 포스팅한다.

    Args:
        carousel_results: instagram_image.generate_daily_carousels() 반환값
        target: 대상 날짜

    Returns:
        포스팅 결과 리스트
    """
    if not INSTAGRAM_ENABLED:
        print("  [Instagram] INSTAGRAM_ENABLED=false → 포스팅 스킵")
        print(f"  [Instagram] 이미지 {len(carousel_results)}건 생성 완료 (로컬 저장만)")
        return []

    if not INSTAGRAM_IMAGE_HOST:
        print("  [Instagram] INSTAGRAM_IMAGE_HOST 미설정 → 포스팅 스킵")
        print("  [Instagram] 이미지를 호스팅한 뒤 URL을 설정해야 합니다")
        return []

    if isinstance(target, str):
        target = date.fromisoformat(target)

    results = []
    for cr in carousel_results:
        item = cr["item"]
        images = cr["images"]
        out_dir = cr["out_dir"]

        # 이미지 URL 생성 (호스팅 베이스 + 상대 경로)
        image_urls = []
        for img_path in images:
            rel_path = img_path.relative_to(Path(__file__).resolve().parent.parent)
            url = f"{INSTAGRAM_IMAGE_HOST}/{rel_path}"
            image_urls.append(url)

        caption = _build_caption(item, target)

        print(f"\n  [Instagram 포스팅] {item['source']} | {item['title'][:40]}")
        result = post_carousel(image_urls, caption)

        if result:
            results.append({
                "item_title": item["title"],
                "item_source": item["source"],
                "post_id": result["id"],
                "image_count": len(images),
                "status": "ok",
            })
        else:
            results.append({
                "item_title": item["title"],
                "item_source": item["source"],
                "post_id": "",
                "image_count": len(images),
                "status": "failed",
            })

        time.sleep(10)  # API rate limit 대응

    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"\n  [Instagram] 포스팅 완료: {ok_count}/{len(results)}건")
    return results


if __name__ == "__main__":
    import sys
    from briefingroom.instagram_image import generate_daily_carousels

    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    carousels = generate_daily_carousels(target_date)
    post_daily_carousels(carousels, target_date)
