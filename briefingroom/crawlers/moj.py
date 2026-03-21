from __future__ import annotations

from .common import *

def crawl_moj(target):
    """법무부 — Playwright"""
    print("\n[법무부]")
    return pw_crawl_list("법무부",
        "https://www.moj.go.kr/moj/226/subview.do?page=1",
        "https://www.moj.go.kr", target)
