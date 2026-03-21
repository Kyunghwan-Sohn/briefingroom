from __future__ import annotations

from .common import *

def crawl_moleg(target):
    """법제처 — Playwright (직접 목록 접근)"""
    print("\n[법제처]")
    return pw_crawl_list("법제처",
        "https://www.moleg.go.kr/board.es?mid=a10501000000&bid=0048&nPage=1",
        "https://www.moleg.go.kr", target, skip_main=True)
