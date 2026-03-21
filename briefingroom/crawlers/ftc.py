from __future__ import annotations

from .common import *

def crawl_ftc(target):
    """공정거래위원회 — Playwright"""
    print("\n[공정거래위원회]")
    return pw_crawl_list("공정거래위원회",
        "https://www.ftc.go.kr/www/selectReportUserView.do?key=10&rpttype=1&pageUnit=10&pageIndex=1",
        "https://www.ftc.go.kr", target, skip_main=True)
