from __future__ import annotations

from .common import *

def crawl_mpm(target):
    """인사혁신처 — Playwright (boardDownload 패턴)"""
    print("\n[인사혁신처]")
    return pw_crawl_list("인사혁신처",
        "https://www.mpm.go.kr/mpm/comm/newsPress/newsPressRelease/?pageIndex=1",
        "https://www.mpm.go.kr", target)
