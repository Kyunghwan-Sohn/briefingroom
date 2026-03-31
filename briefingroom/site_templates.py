"""공통 헤더/푸터/네비 표준 템플릿

모든 정적 페이지(finlaw, weekly, schedule, tools 등)가 이 모듈을 사용합니다.
디자인: 네이비(#1a1a2e) + 골드(#c9a84c), Pretendard + Noto Serif KR
"""
from __future__ import annotations

import html

SITE_NAV_CSS = """
.topnav{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 18px;background:#1a1a2e;border-bottom:2px solid #c9a84c;color:#fff}
.topnav-brand{font-family:'Noto Serif KR',serif;font-size:17px;font-weight:900;color:#fff;text-decoration:none;letter-spacing:-.03em}
.topnav-links{display:flex;align-items:center;gap:2px}
.topnav-link{display:inline-flex;align-items:center;justify-content:center;min-height:34px;padding:6px 14px;border-radius:4px;border:none;background:transparent;color:rgba(255,255,255,.7);font-family:'Pretendard',sans-serif;font-size:13px;font-weight:600;text-decoration:none;transition:all .15s}
.topnav-link.active{background:rgba(201,168,76,.15);color:#c9a84c}
.topnav-link:hover{color:#fff;background:rgba(255,255,255,.08)}
.topnav-bell{color:rgba(255,255,255,.5);font-size:13px;text-decoration:none;display:flex;align-items:center;gap:4px;padding:6px 10px}
.topnav-bell:hover{color:#c9a84c}
.crosslinks{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 20px}
.crosslink{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:7px 14px;border-radius:6px;border:1px solid #e0ddd7;background:#fff;color:#1c1b18;font-size:12px;font-weight:600;text-decoration:none;transition:all .15s}
.crosslink:hover{border-color:#c9a84c;color:#1a1a2e;background:#faf8f3}
.site-footer{margin-top:48px;padding:24px 0;border-top:1px solid #e0ddd7;text-align:center;font-size:11px;color:#96938c;line-height:1.8}
.site-footer a{color:#1a1a2e;text-decoration:none;font-weight:600}
.site-footer a:hover{color:#c9a84c}
@media(max-width:768px){.topnav{padding:10px 14px;gap:8px}.topnav-links{gap:0}.topnav-link{font-size:12px;padding:6px 10px}}
"""


def render_top_nav(active: str = "") -> str:
    links = [
        ("/", "정책브리핑", "brief"),
        ("/finlaw/", "금융법령AI", "finlaw"),
    ]
    parts = []
    for href, label, key in links:
        cls = "topnav-link active" if key == active else "topnav-link"
        parts.append(f'<a class="{cls}" href="{href}">{html.escape(label)}</a>')

    return (
        '<nav class="topnav" aria-label="글로벌 메뉴">'
        '<a class="topnav-brand" href="/">브리핑룸</a>'
        f'<div class="topnav-links">{"".join(parts)}</div>'
        '<a class="topnav-bell" href="https://t.me/govbrief" target="_blank" rel="noopener">🔔 알림</a>'
        "</nav>"
    )


def render_footer() -> str:
    return """<footer class="site-footer">
      <a href="/">정책브리핑</a> · <a href="/finlaw/">금융법령AI</a> · <a href="https://t.me/govbrief" target="_blank" rel="noopener">텔레그램</a>
      <br>govbrief.kr — 정부 정책 + 금융법령 AI 분석
    </footer>"""


def render_crosslinks(*links: tuple[str, str]) -> str:
    parts = [
        f'<a class="crosslink" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        for href, label in links
        if href and label
    ]
    if not parts:
        return ""
    return f'<div class="crosslinks" aria-label="관련 페이지">{"".join(parts)}</div>'
