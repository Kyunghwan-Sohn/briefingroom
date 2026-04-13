"""정적 산출물 검증

배포 전 핵심 페이지의 메타, 사이트맵, 내부 링크, 생성 산출물을 확인합니다.

실행: python -m briefingroom.site_audit
"""
from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from briefingroom.config import BASE_DIR

SITE_URL = "https://govbrief.kr"
REQUIRED_FILES = [
    BASE_DIR / "data" / "home-panel.json",
    BASE_DIR / "data" / "opinions-stats.json",
    BASE_DIR / "data" / "regulation-stats.json",
    BASE_DIR / "sitemap.xml",
]
REQUIRED_SITEMAP_URLS = [
    f"{SITE_URL}/",
    f"{SITE_URL}/brief/",
    f"{SITE_URL}/keywords/",
    f"{SITE_URL}/regulation/",
    f"{SITE_URL}/regulation/finlaw/",
    f"{SITE_URL}/regulation/realestate/",
    f"{SITE_URL}/regulation/cross/",
    f"{SITE_URL}/regulation/finlaw-gpt/",
]
META_PAGES = [
    BASE_DIR / "index.html",
    BASE_DIR / "brief" / "index.html",
    BASE_DIR / "keywords" / "index.html",
    BASE_DIR / "regulation" / "index.html",
    BASE_DIR / "regulation" / "finlaw" / "index.html",
    BASE_DIR / "regulation" / "realestate" / "index.html",
    BASE_DIR / "regulation" / "cross" / "index.html",
    BASE_DIR / "regulation" / "finlaw-gpt" / "index.html",
    BASE_DIR / "regulation" / "finlaw" / "opinions" / "index.html",
]
LINK_CHECK_PAGES = [
    BASE_DIR / "index.html",
    BASE_DIR / "brief" / "index.html",
    BASE_DIR / "keywords" / "index.html",
    BASE_DIR / "regulation" / "index.html",
]


def _resolve_path(href: str) -> Path | None:
    href = href.split("#", 1)[0].split("?", 1)[0].strip()
    if not href.startswith("/") or href == "/":
        return BASE_DIR / "index.html" if href == "/" else None
    path = BASE_DIR / href.lstrip("/")
    if path.is_dir():
        return path / "index.html"
    if path.suffix:
        return path
    return path / "index.html"


def _check_required_files(errors: list[str]) -> None:
    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"필수 산출물 없음: {path}")


def _check_sitemap(errors: list[str]) -> None:
    sitemap = (BASE_DIR / "sitemap.xml").read_text(encoding="utf-8")
    for url in REQUIRED_SITEMAP_URLS:
        if url not in sitemap:
            errors.append(f"sitemap 누락: {url}")


def _check_meta(errors: list[str]) -> None:
    for path in META_PAGES:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        if not soup.find("meta", attrs={"name": "description"}):
            errors.append(f"description 누락: {path}")
        if not soup.find("link", attrs={"rel": "canonical"}):
            errors.append(f"canonical 누락: {path}")
        if not soup.find("meta", attrs={"property": "og:url"}):
            errors.append(f"og:url 누락: {path}")


def _check_links(errors: list[str]) -> None:
    for path in LINK_CHECK_PAGES:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if href.startswith(("http://", "https://", "mailto:", "javascript:")):
                continue
            resolved = _resolve_path(href)
            if resolved and not resolved.exists():
                errors.append(f"깨진 내부 링크: {path} -> {href}")


def _check_home_binding(errors: list[str]) -> None:
    text = (BASE_DIR / "index.html").read_text(encoding="utf-8")
    for token in ("/data/home-panel.json", "/data/regulation-stats.json"):
        if token not in text:
            errors.append(f"홈 데이터 바인딩 누락: {token}")


def main() -> int:
    errors: list[str] = []
    _check_required_files(errors)
    if (BASE_DIR / "sitemap.xml").exists():
        _check_sitemap(errors)
    _check_meta(errors)
    _check_links(errors)
    _check_home_binding(errors)

    if errors:
        print("[site_audit] 실패")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)

    print("[site_audit] 통과")
    return 0


if __name__ == "__main__":
    main()
