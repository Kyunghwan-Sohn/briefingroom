from __future__ import annotations

import ssl

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


class LegacyTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def build_session(
    *,
    headers: dict[str, str] | None = None,
    retries: int = 2,
    legacy_tls_prefixes: tuple[str, ...] = (),
) -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    if headers:
        session.headers.update(headers)
    for prefix in legacy_tls_prefixes:
        session.mount(prefix, LegacyTLSAdapter(max_retries=retries))
    return session
