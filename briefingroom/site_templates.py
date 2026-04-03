"""공통 헤더/푸터/네비 표준 템플릿

모든 정적 페이지(finlaw, weekly, schedule, tools 등)가 이 모듈을 사용합니다.
디자인: G03 소프트그레이+오렌지(#d96c2c), Wanted Sans + Gowun Batang

*** 이 파일이 유일한 헤더 소스입니다 ***
헤더/푸터를 수정할 때는 반드시 여기만 수정하세요.
"""
from __future__ import annotations

import html

# G03 디자인 시스템 -- 공통 CSS 변수 + 폰트 + 기본 리셋
SITE_BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#fafafa;--s:#fff;--b:#c8c8c8;--bl:#e0e0e0;--t:#222;--t2:#555;--m:#999;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace;
--policy:#1e40af;--policy-bg:#eff6ff;--policy-border:#bfdbfe;
--law:#047857;--law-bg:#ecfdf5;--law-border:#a7f3d0}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--t);font-family:var(--sans);max-width:960px;margin:0 auto;padding:58px 0 0;-webkit-font-smoothing:antialiased}
"""

SITE_NAV_CSS = """
.hdr{position:fixed;top:0;left:0;right:0;z-index:50;max-width:960px;margin:0 auto;background:#f5f5f5;border-bottom:3px solid var(--a);height:54px;display:flex;align-items:center;padding:0 12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.logo{font-family:var(--serif);font-size:18px;font-weight:700;color:var(--t);text-decoration:none;margin-right:10px;white-space:nowrap;flex-shrink:0}
.hnav{display:flex;gap:4px;align-items:center;flex:1;min-width:0;overflow-x:auto;-webkit-overflow-scrolling:touch}
.hnav::-webkit-scrollbar{display:none}
.hnav a{font-family:var(--sans);font-size:12px;font-weight:600;color:var(--t2);text-decoration:none;padding:6px 10px;border-radius:6px;white-space:nowrap;background:var(--s);border:1px solid var(--bl);flex-shrink:0}
.hnav a:hover{border-color:var(--a);color:var(--a)}
.hnav a.on{color:#fff;background:var(--a);border-color:var(--a);font-weight:700}
.hnav a.on-policy{color:#fff;background:var(--policy);border-color:var(--policy);font-weight:700}
.hnav a.on-law{color:#fff;background:var(--law);border-color:var(--law);font-weight:700}
.bell{color:var(--m);text-decoration:none;font-family:var(--sans);font-size:11px;font-weight:600;margin-left:auto;flex-shrink:0;white-space:nowrap}
.site-footer{padding:20px 24px;text-align:center;font-size:10px;color:var(--m)}.site-footer a{color:var(--t);text-decoration:none;font-weight:600}
@media(max-width:768px){body{padding-top:48px}.hdr{height:48px;padding:0 10px}.logo{font-size:16px;margin-right:8px}.hnav{gap:3px}.hnav a{font-size:11px;padding:5px 7px}}
"""

SITE_FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="preconnect" href="https://cdn.jsdelivr.net">'
    '<link href="https://cdn.jsdelivr.net/gh/niceplugin/wantedsans@1.0.0/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">'
    '<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'
)

# 네비게이션 탭 정의 (순서 고정)
_NAV_LINKS = [
    ("/", "홈", "home"),
    ("/policy/", "정부 정책 AI", "policy"),
    ("/finlaw/", "금융 법령 AI", "finlaw"),
    ("/articles/", "아카이브", "archive"),
]


def render_top_nav(active: str = "home") -> str:
    """통합 헤더 렌더링. active = home | policy | finlaw | archive"""
    parts = []
    for href, label, key in _NAV_LINKS:
        if key == active:
            if key == "policy":
                cls = "on-policy"
            elif key == "finlaw":
                cls = "on-law"
            else:
                cls = "on"
        else:
            cls = ""
        cls_attr = f' class="{cls}"' if cls else ""
        parts.append(f'<a{cls_attr} href="{href}">{html.escape(label)}</a>')

    return (
        '<header class="hdr">'
        '<a class="logo" href="/">브리핑룸</a>'
        f'<nav class="hnav">{" ".join(parts)}</nav>'
        '<a class="bell" href="https://t.me/govbrief" target="_blank">알림</a>'
        "</header>"
    )


def render_footer() -> str:
    return (
        '<footer class="site-footer">'
        '<a href="/">홈</a> · '
        '<a href="/policy/">정부 정책 AI</a> · '
        '<a href="/finlaw/">금융 법령 AI</a> · '
        '<a href="/articles/">아카이브</a> · '
        '<a href="https://t.me/govbrief" target="_blank">텔레그램</a>'
        '<br>govbrief.kr'
        '</footer>'
    )


def render_crosslinks(*links: tuple[str, str]) -> str:
    parts = [
        f'<a style="display:inline-block;padding:6px 14px;border-radius:8px;border:1px solid var(--b);background:var(--s);color:var(--t);font-size:12px;font-weight:600;text-decoration:none" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        for href, label in links
        if href and label
    ]
    if not parts:
        return ""
    return f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 20px">{"".join(parts)}</div>'
