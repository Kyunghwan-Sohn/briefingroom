from __future__ import annotations

from .common import *

def crawl_mafra(target):
    """농림축산식품부 — Playwright"""
    print("\n[농림축산식품부]")
    return pw_crawl_list("농림축산식품부",
        "https://www.mafra.go.kr/home/5109/subview.do?page=1",
        "https://www.mafra.go.kr", target)
