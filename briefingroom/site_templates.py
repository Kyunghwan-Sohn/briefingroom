"""공통 헤더/푸터/네비 표준 템플릿

모든 정적 페이지(finlaw, weekly, schedule, tools 등)가 이 모듈을 사용합니다.
디자인: G03 소프트그레이+오렌지(#d96c2c), Wanted Sans + Gowun Batang
"""
from __future__ import annotations

import html

# G03 디자인 시스템 — 공통 CSS 변수 + 폰트 + 기본 리셋
SITE_BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--t);font-family:var(--sans);max-width:960px;margin:0 auto;padding:58px 0 0;-webkit-font-smoothing:antialiased}
"""

SITE_NAV_CSS = """
.hdr{position:fixed;top:0;left:0;right:0;z-index:50;max-width:960px;margin:0 auto;background:#f5f5f5;border-bottom:3px solid var(--a);height:54px;display:flex;align-items:center;padding:0 20px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.logo{font-family:var(--serif);font-size:19px;font-weight:700;color:var(--t);text-decoration:none;margin-right:16px;white-space:nowrap}
.hnav{display:flex;gap:0;align-items:center;flex:1;min-width:0}
.hnav a{font-size:14px;font-weight:600;color:var(--m);text-decoration:none;padding:6px 12px;border-radius:5px;white-space:nowrap}
.hnav a.on{color:var(--a);background:var(--al);font-weight:700}
.bell{color:var(--m);text-decoration:none;font-size:16px;margin-left:auto;flex-shrink:0}
.site-footer{padding:20px 24px;text-align:center;font-size:10px;color:var(--m)}.site-footer a{color:var(--t);text-decoration:none;font-weight:600}
@media(max-width:768px){body{padding-top:52px}.hdr{height:50px;padding:0 14px}.logo{font-size:17px;margin-right:10px}.hnav a{font-size:11px;padding:5px 8px}}
"""

SITE_FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="preconnect" href="https://cdn.jsdelivr.net">'
    '<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">'
    '<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'
)


def render_top_nav(active: str = "") -> str:
    links = [
        ("/", "홈", "brief"),
        ("/finlaw/", "금융 법령 AI", "finlaw"),
    ]
    parts = []
    for href, label, key in links:
        cls = "hnav-a on" if key == active else "hnav-a"
        parts.append(f'<a class="{cls}" href="{href}">{html.escape(label)}</a>')

    return (
        '<header class="hdr">'
        '<a class="logo" href="/">브리핑룸</a>'
        f'<nav class="hnav">{"".join(parts)}</nav>'
        '<a class="bell" href="https://t.me/govbrief" target="_blank" rel="noopener">🔔</a>'
        "</header>"
    )


def render_footer() -> str:
    return """<footer class="site-footer">
      <a href="/">홈</a> · <a href="/finlaw/">금융 법령 AI</a> · <a href="https://t.me/govbrief" target="_blank" rel="noopener">텔레그램</a>
      <br>govbrief.kr
    </footer>"""


def render_crosslinks(*links: tuple[str, str]) -> str:
    parts = [
        f'<a style="display:inline-block;padding:6px 14px;border-radius:8px;border:1px solid var(--b);background:var(--s);color:var(--t);font-size:12px;font-weight:600;text-decoration:none" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        for href, label in links
        if href and label
    ]
    if not parts:
        return ""
    return f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 20px">{"".join(parts)}</div>'
