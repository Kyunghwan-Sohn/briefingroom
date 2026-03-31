from __future__ import annotations

import html

SITE_NAV_CSS = """
.topnav{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px;padding:12px 14px;background:#fff;border:1px solid #e0ddd7;border-radius:12px}
.topnav-brand{font-family:'Noto Serif KR',serif;font-size:17px;font-weight:700;color:#1c1b18;text-decoration:none}
.topnav-links{display:flex;flex-wrap:wrap;gap:8px}
.topnav-link{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:8px 12px;border-radius:999px;border:1px solid #e0ddd7;background:#fff;color:#4a4844;font-size:12px;font-weight:600;text-decoration:none}
.topnav-link.active{background:#1a1a2e;border-color:#1a1a2e;color:#fff}
.crosslinks{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 24px}
.crosslink{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:8px 12px;border-radius:10px;border:1px solid #e0ddd7;background:#fff;color:#1c1b18;font-size:12px;font-weight:600;text-decoration:none}
.crosslink:hover,.topnav-link:hover{border-color:#c9a84c;color:#1a1a2e}
@media(max-width:768px){.topnav{align-items:flex-start;flex-direction:column}.topnav-links{width:100%}.topnav-link,.crosslink{flex:1}}
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
