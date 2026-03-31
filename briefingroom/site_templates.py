from __future__ import annotations

import html

SITE_NAV_CSS = """
.topnav{position:sticky;top:16px;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:20px;padding:14px 18px;background:rgba(255,255,255,.96);border:1px solid #d9d5cc;border-radius:14px;backdrop-filter:blur(10px);box-shadow:0 8px 24px rgba(0,0,0,.04)}
.topnav-brand{font-family:'Noto Serif KR',serif;font-size:18px;font-weight:700;color:#16213d;text-decoration:none;letter-spacing:-.02em}
.topnav-links{display:flex;flex-wrap:wrap;gap:8px}
.topnav-link{display:inline-flex;align-items:center;justify-content:center;min-height:38px;padding:8px 12px;border-radius:8px;border:1px solid transparent;background:transparent;color:#4b5563;font-size:13px;font-weight:600;text-decoration:none}
.topnav-link.active{background:#16213d;border-color:#16213d;color:#fff}
.topnav-link:hover{background:#f5f3ee;border-color:#d9d5cc;color:#16213d}
.crosslinks{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 24px}
.crosslink{display:inline-flex;align-items:center;justify-content:center;min-height:38px;padding:8px 12px;border-radius:8px;border:1px solid #d9d5cc;background:#fff;color:#16213d;font-size:13px;font-weight:600;text-decoration:none}
.crosslink:hover{background:#f5f3ee}
@media(max-width:768px){.topnav{top:8px;align-items:flex-start;flex-direction:column;padding:12px 14px}.topnav-links{width:100%}.topnav-link,.crosslink{flex:1}}
"""


def render_top_nav(active: str = "") -> str:
    links = [
        ("/", "메인", ""),
        ("/subsidy/", "지원사업", "subsidy"),
        ("/articles/weekly/", "주간 리포트", "weekly"),
        ("/articles/schedule/", "차주 일정", "schedule"),
    ]
    parts = []
    for href, label, key in links:
        cls = "topnav-link active" if key == active else "topnav-link"
        parts.append(f'<a class="{cls}" href="{href}">{html.escape(label)}</a>')
    return (
        '<nav class="topnav" aria-label="페이지 탐색">'
        '<a class="topnav-brand" href="/">브리핑룸</a>'
        f'<div class="topnav-links">{"".join(parts)}</div>'
        "</nav>"
    )


def render_crosslinks(*links: tuple[str, str]) -> str:
    parts = [
        f'<a class="crosslink" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        for href, label in links
        if href and label
    ]
    if not parts:
        return ""
    return f'<div class="crosslinks" aria-label="관련 페이지 링크">{"".join(parts)}</div>'
