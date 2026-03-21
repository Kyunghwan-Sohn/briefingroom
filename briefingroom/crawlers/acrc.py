from __future__ import annotations

from .common import *

def crawl_acrc(target):
    """국민권익위원회 — Playwright (올바른 보도자료 URL)"""
    print("\n[국민권익위원회]")
    return pw_crawl_list("국민권익위원회",
        "https://www.acrc.go.kr/board.es?mid=a10402010000&bid=4A&nPage=1",
        "https://www.acrc.go.kr", target)
