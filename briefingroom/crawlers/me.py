from __future__ import annotations

from .common import *

def crawl_me(target):
    """환경부 — Playwright"""
    print("\n[환경부]")
    return pw_crawl_list("환경부",
        "https://www.me.go.kr/home/web/board/list.do?menuId=286&boardMasterId=1&boardCategoryId=39&page=1",
        "https://www.me.go.kr", target)
