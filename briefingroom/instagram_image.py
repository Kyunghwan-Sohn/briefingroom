"""인스타그램 캐러셀 이미지 자동 생성

HTML 템플릿 + Playwright 스크린샷으로 1080x1080 카드뉴스를 생성한다.
instagram_content.py에서 생성한 구조화 콘텐츠를 입력으로 받는다.
"""
from __future__ import annotations

import json
import re
import textwrap
from datetime import date
from pathlib import Path

from briefingroom.config import BASE_DIR, CAT_MAP, DATA_DIR

IG_OUT_DIR = BASE_DIR / "instagram"

# ── 디자인 토큰 ──────────────────────────────────────────────
BRAND = {
    "navy": "#1B2838",
    "blue": "#3B82F6",
    "amber": "#F59E0B",
    "white": "#FFFFFF",
    "light": "#F8FAFC",
    "dark_gray": "#374151",
    "light_blue": "#93c5fd",
    "green": "#10B981",
    "red": "#EF4444",
}

CAT_EMOJI = {
    "금융경제": "💰",
    "사회복지": "🏥",
    "산업기술": "⚙️",
    "외교안보": "🌏",
    "행정법제": "📜",
}

IMPACT_STYLE = {
    "상": {"color": "#EF4444", "bg": "#FEE2E2", "label": "영향도 높음"},
    "중": {"color": "#F59E0B", "bg": "#FEF3C7", "label": "영향도 중간"},
    "하": {"color": "#6B7280", "bg": "#F3F4F6", "label": "영향도 낮음"},
}


def _base_style() -> str:
    return """
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
      width: 1080px; height: 1080px;
      font-family: 'Pretendard', -apple-system, sans-serif;
      overflow: hidden;
    }
    .card {
      width: 1080px; height: 1080px;
      position: relative;
      display: flex; flex-direction: column;
    }
    .brand-bar {
      position: absolute; bottom: 0; left: 0; right: 0;
      height: 72px;
      background: linear-gradient(90deg, #1B2838, #2563EB);
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 40px;
    }
    .brand-bar .logo { font-size: 18px; font-weight: 700; color: #fff; letter-spacing: 2px; }
    .brand-bar .page { font-size: 16px; color: rgba(255,255,255,0.6); }
    """


def _dedup_title(title: str) -> str:
    """제목 내 반복 텍스트 제거."""
    n = len(title)
    if n < 20:
        return title
    probe = title[:10]
    second = title.find(probe, 10)
    if second > 10:
        return title[:second].rstrip()
    half = n // 2
    if half > 10 and title[:half].strip() == title[half:].strip():
        return title[:half].strip()
    return title


# ── 표지 카드 ────────────────────────────────────────────────

def _cover_html(content: dict, total_slides: int) -> str:
    """표지 카드 HTML — hook + 원제목(출처) + subtitle"""
    source = content.get("source", "")
    hook = content.get("hook", content.get("title", ""))
    subtitle = content.get("subtitle", "핵심 내용을 정리했습니다")
    orig_title = _dedup_title(content.get("title", ""))
    target_date = content.get("date", "")
    category = content.get("category", CAT_MAP.get(source, "행정법제"))
    impact = content.get("impact", "중")
    imp = IMPACT_STYLE.get(impact, IMPACT_STYLE["중"])
    emoji = CAT_EMOJI.get(category, "📋")

    hook = _dedup_title(hook)

    # 원제목이 hook과 동일하면 중복 표시하지 않음
    show_orig = orig_title and orig_title != hook and len(orig_title) > 5
    # 원제목이 너무 길면 자르기
    if show_orig and len(orig_title) > 45:
        orig_title = orig_title[:42] + "..."

    orig_title_html = f'<div class="orig-title">📋 {orig_title}</div>' if show_orig else ""

    # hook 줄바꿈 처리
    if len(hook) > 18:
        lines = textwrap.wrap(hook, width=12)
        hook_html = "<br>".join(lines[:3])
        font_size = "52px" if len(hook) <= 30 else "44px"
    else:
        hook_html = hook
        font_size = "60px"

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    {_base_style()}
    .card {{
      background: linear-gradient(160deg, #1B2838 0%, #1e3a5f 100%);
      justify-content: center; padding: 72px 64px 120px;
      color: #fff;
    }}
    .dept-badge {{
      display: inline-block;
      background: rgba(59,130,246,0.2);
      border: 1.5px solid rgba(59,130,246,0.5);
      border-radius: 40px;
      padding: 10px 28px;
      font-size: 22px; font-weight: 600;
      color: {BRAND['light_blue']};
      margin-bottom: 28px;
    }}
    .hook {{
      font-size: {font_size}; font-weight: 800;
      line-height: 1.35; margin-bottom: 16px;
      word-break: keep-all;
    }}
    .orig-title {{
      font-size: 18px; color: #64748b;
      line-height: 1.4; margin-bottom: 20px;
      word-break: keep-all;
      padding: 10px 16px;
      background: rgba(255,255,255,0.06);
      border-radius: 8px;
    }}
    .subtitle {{
      font-size: 26px; color: #94a3b8;
      line-height: 1.5; margin-bottom: 36px;
    }}
    .meta {{
      display: flex; align-items: center; gap: 20px;
    }}
    .meta .date {{ font-size: 20px; color: #64748b; letter-spacing: 1px; }}
    .meta .impact {{
      display: inline-block;
      padding: 6px 16px; border-radius: 6px;
      font-size: 16px; font-weight: 700;
      background: {imp['bg']}; color: {imp['color']};
    }}
    </style></head><body>
    <div class="card">
      <div class="dept-badge">{emoji} {source}</div>
      <div class="hook">{hook_html}</div>
      {orig_title_html}
      <div class="subtitle">{subtitle}</div>
      <div class="meta">
        <span class="date">{target_date}</span>
        <span class="impact">{imp['label']}</span>
      </div>
      <div class="brand-bar">
        <span class="logo">BRIEFINGROOM</span>
        <span class="page">밀어서 보기 →</span>
      </div>
    </div>
    </body></html>"""


# ── 본문 포인트 카드 ─────────────────────────────────────────

def _point_html(point: dict, point_idx: int,
                slide_num: int, total_slides: int) -> str:
    """본문 포인트 카드 HTML — title + detail + highlight 사용"""
    num = f"{point_idx + 1:02d}"
    title = point.get("title", f"핵심 {point_idx + 1}")
    detail = point.get("detail", "")
    highlight = point.get("highlight", "")

    # detail을 충분히 보여줌 (최대 180자)
    if len(detail) > 180:
        detail = detail[:177] + "..."

    highlight_html = ""
    if highlight:
        highlight_html = f"""
        <div class="highlight">
          <span class="hl-icon">💡</span>
          <span class="hl-text">{highlight}</span>
        </div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    {_base_style()}
    .card {{
      background: #FFFFFF;
      padding: 56px 52px 100px;
    }}
    .num {{
      position: absolute; top: 24px; right: 44px;
      font-size: 120px; font-weight: 900;
      color: {BRAND['blue']}; opacity: 0.07;
      line-height: 1;
    }}
    .label {{
      font-size: 18px; font-weight: 700;
      color: {BRAND['blue']};
      letter-spacing: 3px;
      margin-bottom: 20px;
    }}
    .point-title {{
      font-size: 38px; font-weight: 800;
      color: {BRAND['navy']};
      line-height: 1.35;
      margin-bottom: 28px;
      word-break: keep-all;
    }}
    .point-detail {{
      font-size: 24px;
      color: {BRAND['dark_gray']};
      line-height: 1.8;
      word-break: keep-all;
      margin-bottom: 28px;
    }}
    .highlight {{
      padding: 18px 22px;
      background: {BRAND['light']};
      border-left: 4px solid {BRAND['blue']};
      border-radius: 0 12px 12px 0;
      display: flex; align-items: center; gap: 12px;
    }}
    .hl-icon {{ font-size: 22px; }}
    .hl-text {{
      font-size: 22px; font-weight: 700;
      color: {BRAND['navy']};
      line-height: 1.4;
    }}
    </style></head><body>
    <div class="card">
      <div class="num">{num}</div>
      <div class="label">POINT {num}</div>
      <div class="point-title">{title}</div>
      <div class="point-detail">{detail}</div>
      {highlight_html}
      <div class="brand-bar">
        <span class="logo">BRIEFINGROOM</span>
        <span class="page">{slide_num} / {total_slides}</span>
      </div>
    </div>
    </body></html>"""


# ── CTA 카드 ─────────────────────────────────────────────────

def _cta_html(content: dict, total_slides: int) -> str:
    """CTA(마지막) 카드 HTML — impact_line 사용"""
    impact_line = content.get("impact_line", "")
    impact_html = f'<div class="impact-line">{impact_line}</div>' if impact_line else ""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    {_base_style()}
    .card {{
      background: linear-gradient(160deg, #1B2838 0%, #0f172a 100%);
      justify-content: center; align-items: center;
      text-align: center;
      padding: 80px 64px 120px;
      color: #fff;
    }}
    .cta-icon {{
      width: 96px; height: 96px; border-radius: 50%;
      background: rgba(59,130,246,0.2);
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 40px; font-size: 40px;
    }}
    .impact-line {{
      font-size: 28px; font-weight: 600;
      color: {BRAND['amber']};
      margin-bottom: 32px;
      line-height: 1.4;
    }}
    .cta-text {{
      font-size: 40px; font-weight: 700;
      line-height: 1.5; margin-bottom: 16px;
    }}
    .cta-sub {{
      font-size: 24px; color: #94a3b8;
      margin-bottom: 48px;
    }}
    .cta-handle {{
      display: inline-block;
      font-size: 26px; font-weight: 600;
      color: {BRAND['blue']};
      padding: 16px 40px;
      border: 2px solid rgba(59,130,246,0.4);
      border-radius: 48px;
    }}
    </style></head><body>
    <div class="card">
      <div class="cta-icon">📌</div>
      {impact_html}
      <div class="cta-text">더 자세한 내용은<br>프로필 링크에서<br>확인하세요</div>
      <div class="cta-sub">매일 오전, AI가 요약한 정책 브리핑</div>
      <div class="cta-handle">@govbrief.kr</div>
      <div class="brand-bar">
        <span class="logo">BRIEFINGROOM</span>
        <span class="page">{total_slides} / {total_slides}</span>
      </div>
    </div>
    </body></html>"""


# ── 메인 생성 함수 ────────────────────────────────────────────

def generate_carousel_from_content(content: dict, out_dir: Path) -> list[Path]:
    """구조화된 콘텐츠(instagram_content.py 출력)로 캐러셀 이미지를 생성한다.

    Args:
        content: generate_carousel_content() 또는 _fallback_from_summary() 반환값
        out_dir: 이미지 저장 디렉토리

    Returns:
        생성된 이미지 파일 경로 리스트
    """
    from playwright.sync_api import sync_playwright

    points = content.get("points", [])
    total_slides = 1 + len(points) + 1
    html_pages: list[str] = []

    # 1. 표지
    html_pages.append(_cover_html(content, total_slides))

    # 2. 본문 포인트들
    for idx, pt in enumerate(points):
        html_pages.append(_point_html(pt, idx, idx + 2, total_slides))

    # 3. CTA
    html_pages.append(_cta_html(content, total_slides))

    out_dir.mkdir(parents=True, exist_ok=True)
    image_paths: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080})

        for slide_idx, html in enumerate(html_pages):
            page.set_content(html, wait_until="networkidle")
            page.wait_for_timeout(800)

            out_path = out_dir / f"slide_{slide_idx:02d}.png"
            page.screenshot(path=str(out_path), type="png")
            image_paths.append(out_path)

        browser.close()

    return image_paths


def generate_daily_carousels(target: date | str) -> list[dict]:
    """일일 JSON에서 top3 기사의 콘텐츠를 생성하고 캐러셀 이미지를 만든다.

    Returns:
        [{"content": dict, "images": [Path, ...], "out_dir": Path}, ...]
    """
    from briefingroom.instagram_content import generate_carousel_content

    if isinstance(target, str):
        target = date.fromisoformat(target)

    json_path = DATA_DIR / f"{target.isoformat()}.json"
    if not json_path.exists():
        print(f"  [Instagram] JSON 없음: {json_path}")
        return []

    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        print("  [Instagram] 기사 0건 → 스킵")
        return []

    # top3 선정
    top3_indices = data.get("top3", [])
    if not top3_indices:
        scored = []
        for i, it in enumerate(items):
            imp_score = {"상": 3, "중": 2, "하": 1}.get(it.get("impact", "중"), 2)
            has_sum = 1 if it.get("summary") else 0
            scored.append((imp_score, has_sum, i))
        scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
        top3_indices = [s[2] for s in scored[:3]]

    day_dir = IG_OUT_DIR / target.isoformat()

    results = []
    for rank, idx in enumerate(top3_indices):
        if idx >= len(items):
            continue
        item = items[idx]
        if not item.get("summary"):
            continue

        print(f"  [Instagram] #{rank+1} {item['source']} | {item['title'][:40]}")

        # 1단계: 콘텐츠 생성 (LLM 또는 fallback)
        content = generate_carousel_content(item)
        if not content:
            continue

        is_fb = " (fallback)" if content.get("_is_fallback") else ""
        print(f"    콘텐츠: {content.get('hook', '')}{is_fb}")
        for i, pt in enumerate(content.get("points", [])):
            print(f"    P{i+1}: {pt.get('title', '')} — {pt.get('highlight', '')}")

        # 2단계: 이미지 생성
        article_dir = day_dir / f"{rank:02d}_{_safe_dirname(item.get('source', ''))}"
        try:
            images = generate_carousel_from_content(content, article_dir)
            results.append({
                "content": content,
                "item": item,
                "images": images,
                "out_dir": article_dir,
                "rank": rank,
            })
            print(f"    → {len(images)}장 생성: {article_dir}")
        except Exception as e:
            print(f"    → 생성 실패: {e}")

    return results


def _safe_dirname(name: str) -> str:
    return re.sub(r'[^\w가-힣]', '_', name).strip('_')[:20]


if __name__ == "__main__":
    import sys
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    results = generate_daily_carousels(target_date)
    print(f"\n총 {len(results)}건의 캐러셀 생성 완료")
    for r in results:
        src = r["content"].get("source", "")
        print(f"  {src}: {len(r['images'])}장 → {r['out_dir']}")
