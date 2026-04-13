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
*{box-sizing:border-box;margin:0;padding:0;word-break:keep-all;overflow-wrap:break-word}
:root{--a:#d96c2c;--al:rgba(217,108,44,.06);--ab:rgba(217,108,44,.15);--bg:#f7f7f5;--s:#fff;--s2:#fafaf8;--b:#dcdcd8;--bl:#ededea;--t:#1a1a1a;--t2:#555;--t3:#888;--m:#bbb;--serif:'Gowun Batang',serif;--sans:'Wanted Sans Variable',sans-serif;--mono:'JetBrains Mono',monospace;
--policy:#1e40af;--policy-bg:#eff6ff;--policy-border:#bfdbfe;
--law:#047857;--law-bg:#ecfdf5;--law-border:#a7f3d0}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--t);font-family:var(--sans);-webkit-font-smoothing:antialiased;font-size:15px;line-height:1.6;min-width:1120px;max-width:none;margin:0;padding:0}
.is-mobile body{min-width:0;font-size:14px;line-height:1.55;padding-bottom:68px}
"""

SITE_NAV_CSS = """
.hdr{background:#fff;border-bottom:1px solid var(--b);height:64px;display:flex;align-items:center;padding:0 32px;position:sticky;top:0;z-index:100;width:max(100vw,1120px);max-width:none;margin-left:calc(50% - 50vw);box-shadow:none}
.hdr-logo,.logo{font-family:var(--serif);font-size:24px;font-weight:700;color:var(--t);text-decoration:none;margin-right:44px;white-space:nowrap;flex-shrink:0}
.hdr-nav,.hnav{display:flex;gap:6px;align-items:center;flex:1;min-width:0;overflow:visible}
.hdr-nav::-webkit-scrollbar,.hnav::-webkit-scrollbar{display:none}
.hdr-nav a,.hnav a{font-family:var(--sans);font-size:15px;font-weight:600;color:var(--t2);text-decoration:none;padding:10px 16px;border-radius:6px;white-space:nowrap;background:transparent;border:0;flex-shrink:0}
.hdr-nav a:hover,.hnav a:hover{background:var(--bl);color:var(--t2)}
.hdr-nav a.on,.hnav a.on{color:var(--a);background:var(--al);font-weight:700}
.hdr-nav a.on-policy,.hnav a.on-policy{color:var(--policy);background:var(--policy-bg);font-weight:700}
.hdr-nav a.on-law,.hnav a.on-law{color:var(--law);background:var(--law-bg);font-weight:700}
.hdr-nav .lbl-short,.hnav .lbl-short{display:none}
.hdr-search{position:relative;width:280px;margin-right:16px}
.hdr-search input{width:100%;padding:10px 14px 10px 36px;font-size:13px;border:1px solid var(--b);border-radius:6px;background:var(--s2);outline:none;font-family:var(--sans);color:var(--t)}
.hdr-search input:focus{border-color:var(--a);background:#fff}
.hdr-search input::placeholder{color:var(--m)}
.hdr-search-icon{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--m);font-size:15px}
.hdr-time{font-family:var(--mono);font-size:12px;color:var(--t3)}
.bell{display:none}
.mobile-search{display:none}
.is-mobile .mobile-search{display:block;background:#fff;padding:10px 14px;border-bottom:1px solid var(--bl);position:sticky;top:52px;z-index:90}
.mobile-search-box{position:relative}
.mobile-search-box input{width:100%;padding:10px 14px 10px 36px;font-size:13px;border:1px solid var(--b);border-radius:8px;background:var(--s2);outline:none;font-family:var(--sans);color:var(--t)}
.mobile-search-box input:focus{border-color:var(--a);background:#fff}
.mobile-search-icon{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--m);font-size:14px;pointer-events:none}
.site-footer{padding:24px 16px 32px;text-align:center;font-size:12px;color:var(--t3);border-top:1px solid var(--bl);max-width:1240px;margin:20px auto 0}
.site-footer a{color:var(--t3);text-decoration:none;font-weight:600}
.bottom-nav,.bnav{display:none}
.bottom-nav a,.bnav a{display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;color:var(--t3);font-size:10.5px;font-weight:600;padding:4px 0}
.bottom-nav a.on,.bnav a.on{color:var(--a)}
.bottom-nav svg,.bnav svg{width:22px;height:22px;stroke-width:2;fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round}
.bottom-nav a.on svg,.bnav a.on svg{stroke-width:2.4}
.is-mobile .hdr{height:52px;padding:0 12px;gap:4px;width:100%;margin-left:0}
.is-mobile .hdr-logo,.is-mobile .logo{font-size:17px;margin-right:8px}
.is-mobile .hdr-nav,.is-mobile .hnav{gap:2px;flex:1;min-width:0}
.is-mobile .hdr-nav a,.is-mobile .hnav a{font-size:12px;padding:7px 8px}
.is-mobile .hdr-nav .lbl-full,.is-mobile .hnav .lbl-full{display:none}
.is-mobile .hdr-nav .lbl-short,.is-mobile .hnav .lbl-short{display:inline}
.is-mobile .hdr-search,.is-mobile .hdr-time{display:none}
.is-mobile .bottom-nav,.is-mobile .bnav{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;bottom:0;left:0;right:0;z-index:200;background:#fff;border-top:1px solid var(--b);padding:8px 0 calc(10px + env(safe-area-inset-bottom));box-shadow:0 -2px 12px rgba(0,0,0,.06)}
.is-mobile .site-footer{padding:18px 14px 22px;font-size:10px}
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
    ("/brief/", "정부 발표", "brief"),
    ("/keywords/", "키워드 분석", "keywords"),
    ("/regulation/", "금융/부동산 규제", "regulation"),
]


def render_top_nav(active: str = "home") -> str:
    """통합 헤더 렌더링. active = home | brief | keywords | regulation"""
    active = {
        "policy": "brief",
        "weekly": "brief",
        "schedule": "brief",
        "archive": "brief",
        "finlaw": "regulation",
        "law": "regulation",
    }.get(active, active)
    parts = []
    for href, label, key in _NAV_LINKS:
        short = "키워드" if key == "keywords" else "금융/부동산" if key == "regulation" else label
        if key == active:
            if key == "brief":
                cls = "on-policy"
            elif key == "regulation":
                cls = "on-law"
            else:
                cls = "on"
        else:
            cls = ""
        cls_attr = f' class="{cls}"' if cls else ""
        parts.append(
            f'<a{cls_attr} href="{href}">'
            f'<span class="lbl-full">{html.escape(label)}</span>'
            f'<span class="lbl-short">{html.escape(short)}</span>'
            '</a>'
        )

    return (
        '<header class="hdr">'
        '<a class="hdr-logo" href="/">브리핑룸</a>'
        f'<nav class="hdr-nav">{" ".join(parts)}</nav>'
        '<div class="hdr-search"><span class="hdr-search-icon">&#x2315;</span><input placeholder="검색"></div>'
        '<div class="hdr-time">2026.04.13</div>'
        "</header>"
        '<div class="mobile-search"><div class="mobile-search-box"><span class="mobile-search-icon">&#x2315;</span><input placeholder="검색"></div></div>'
    )


def render_footer() -> str:
    return (
        '<footer class="site-footer">'
        '<a href="/">홈</a> · '
        '<a href="/brief/">정부 발표</a> · '
        '<a href="/keywords/">키워드 분석</a> · '
        '<a href="/regulation/">금융/부동산 규제</a> · '
        '<a href="https://t.me/govbrief" target="_blank">텔레그램</a>'
        '<br>govbrief.kr'
        '</footer>'
    )


def render_bottom_nav(active: str = "home") -> str:
    """모바일 하단 4탭 네비 렌더링."""
    active = {
        "policy": "brief",
        "weekly": "brief",
        "schedule": "brief",
        "archive": "brief",
        "finlaw": "regulation",
        "law": "regulation",
    }.get(active, active)

    def cls(key: str) -> str:
        return ' class="on"' if key == active else ""

    return (
        '<nav class="bottom-nav">'
        f'<a{cls("home")} href="/"><svg viewBox="0 0 24 24"><path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V10.5z"/></svg><span>홈</span></a>'
        f'<a{cls("brief")} href="/brief/"><svg viewBox="0 0 24 24"><path d="M4 5h16v14H4z"/><path d="M8 9h8M8 13h8M8 17h5"/></svg><span>정부 발표</span></a>'
        f'<a{cls("keywords")} href="/keywords/"><svg viewBox="0 0 24 24"><path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/></svg><span>키워드</span></a>'
        f'<a{cls("regulation")} href="/regulation/"><svg viewBox="0 0 24 24"><path d="M12 3v18M5 7h14"/><path d="M5 7l-2 6a4 4 0 0 0 8 0l-2-6M19 7l-2 6a4 4 0 0 0 8 0l-2-6"/></svg><span>금융/부동산</span></a>'
        "</nav>"
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
