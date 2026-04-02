from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from briefingroom import app as app_module
from briefingroom import db as db_module
from briefingroom import files as files_module
from briefingroom import http as http_module
from briefingroom import llm as llm_module
from briefingroom import detail_gen as detail_gen_module
from briefingroom import finlaw_gpt as finlaw_gpt_module
from briefingroom import subsidy as subsidy_module
from briefingroom import telegram as telegram_module
from briefingroom import weekly_analysis as weekly_analysis_module
from briefingroom import wordpress as wordpress_module


class FakeResponse:
    def __init__(self, headers: dict[str, str], chunks: list[bytes]):
        self.headers = headers
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, _size: int):
        for chunk in self._chunks:
            yield chunk


class FakeSession:
    def __init__(self, response):
        self.response = response

    def get(self, *_args, **_kwargs):
        return self.response


class FakeQuotaResponse:
    status_code = 429
    text = "daily quota exceeded"
    headers = {"Content-Type": "application/json"}

    def json(self):
        return {}


class RegressionTests(unittest.TestCase):
    def test_clean_titles_normalizes_and_truncates(self):
        items = [{
            "title": "  테스트\xa0제목  테스트\xa0제목  " * 8,
        }]

        cleaned = app_module._clean_titles(items)

        self.assertEqual(cleaned, 1)
        self.assertLessEqual(len(items[0]["title"]), 120)
        self.assertNotIn("\xa0", items[0]["title"])

    def test_bulk_upsert_refreshes_file_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_db_path = db_module.DB_PATH
            db_module.DB_PATH = Path(tmpdir) / "briefingroom.db"
            try:
                db_module.init_db()
                item = {
                    "date": "2026-03-27",
                    "source": "금융위원회",
                    "title": "테스트",
                    "url": "https://example.com/a",
                    "pdfs": ["https://example.com/a.pdf"],
                    "hwps": [],
                    "text": "",
                    "summary": "",
                }
                db_module.bulk_upsert([item])

                item["text"] = "본문"
                item["url"] = "https://example.com/b"
                db_module.bulk_upsert([item])

                conn = db_module._conn()
                row = conn.execute(
                    "SELECT url, file_status, text_length, pdf_count FROM articles WHERE date=? AND source=? AND title=?",
                    (item["date"], item["source"], item["title"]),
                ).fetchone()
                conn.close()
                self.assertEqual(row["url"], "https://example.com/b")
                self.assertEqual(row["file_status"], "ok")
                self.assertEqual(row["text_length"], 2)
                self.assertEqual(row["pdf_count"], 1)
            finally:
                db_module.DB_PATH = original_db_path

    def test_download_file_rejects_oversized_content_length(self):
        response = FakeResponse(
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": str(files_module.MAX_DOWNLOAD_BYTES + 1),
            },
            chunks=[b"%PDF-1.4"],
        )

        result = files_module.download_file(
            "https://example.com/too-big.pdf",
            "too_big_test.pdf",
            FakeSession(response),
        )

        self.assertIsNone(result)
        self.assertFalse((files_module.PDF_DIR / "too_big_test.pdf").exists())

    def test_download_file_rejects_invalid_signature(self):
        response = FakeResponse(
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": "12",
            },
            chunks=[b"not-a-pdf"],
        )

        result = files_module.download_file(
            "https://example.com/invalid.pdf",
            "invalid_signature_test.pdf",
            FakeSession(response),
        )

        self.assertIsNone(result)
        self.assertFalse((files_module.PDF_DIR / "invalid_signature_test.pdf").exists())

    def test_save_text_uses_stable_suffix_to_avoid_collisions(self):
        item1 = {
            "date": "2026-03-27",
            "source": "금융위원회",
            "title": "같은 제목",
            "url": "https://example.com/a",
        }
        item2 = {
            "date": "2026-03-27",
            "source": "금융위원회",
            "title": "같은 제목",
            "url": "https://example.com/b",
        }

        path1 = files_module.save_text(item1, "본문1")
        path2 = files_module.save_text(item2, "본문2")

        try:
            self.assertNotEqual(path1.name, path2.name)
        finally:
            path1.unlink(missing_ok=True)
            path2.unlink(missing_ok=True)

    def test_llm_quota_exhaustion_sets_global_flag(self):
        original_post = llm_module.requests.post
        original_quota = llm_module._quota_exhausted
        llm_module.requests.post = lambda *args, **kwargs: FakeQuotaResponse()
        llm_module._quota_exhausted = False
        try:
            result = llm_module._chat_completion([{"role": "user", "content": "테스트"}])
            self.assertIn("한도 초과", result)
            self.assertTrue(llm_module._quota_exhausted)
        finally:
            llm_module.requests.post = original_post
            llm_module._quota_exhausted = original_quota

    def test_detail_markdown_renderer_escapes_html(self):
        html_out = detail_gen_module._md_to_html("### 제목\n- <script>alert(1)</script>\n**강조**")
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html_out)
        self.assertNotIn("<script>alert(1)</script>", html_out)
        self.assertIn("<strong>강조</strong>", html_out)

    def test_finlaw_gpt_returns_clear_error_without_llm_key(self):
        original_llm_key = finlaw_gpt_module.LLM_API_KEY
        original_search = finlaw_gpt_module.search_context
        finlaw_gpt_module.LLM_API_KEY = ""
        finlaw_gpt_module.search_context = lambda _q: {
            "laws": [{"name": "자본시장법", "ministry": "금융위원회", "revision_type": "일부개정", "amendment_reason": ""}],
            "articles": [],
            "precedents": [],
            "interpretations": [],
            "errors": [],
        }
        try:
            result = finlaw_gpt_module.ask("테스트 질문")
            self.assertIn("LLM_API_KEY", result["answer"])
            self.assertEqual(result["sources"]["laws"], 1)
        finally:
            finlaw_gpt_module.LLM_API_KEY = original_llm_key
            finlaw_gpt_module.search_context = original_search

    def test_wp_post_fails_closed_on_duplicate_lookup_error(self):
        original_check = wordpress_module.wp_check_duplicate
        wordpress_module.wp_check_duplicate = lambda *_args, **_kwargs: None
        try:
            with self.assertRaisesRegex(RuntimeError, "중복 체크 실패"):
                wordpress_module.wp_post({
                    "title": "테스트 포스트",
                    "date": "2026-03-27",
                    "source": "금융위원회",
                    "summary": "요약: 내용\n키워드: 금융",
                    "url": "https://example.com/source",
                    "files": [],
                })
        finally:
            wordpress_module.wp_check_duplicate = original_check

    def test_build_session_limits_legacy_tls_to_configured_prefixes(self):
        session = http_module.build_session(
            legacy_tls_prefixes=("https://www.korea.kr/",),
        )

        self.assertIsInstance(
            session.get_adapter("https://www.korea.kr/test"),
            http_module.LegacyTLSAdapter,
        )
        self.assertNotIsInstance(
            session.get_adapter("https://example.com/test"),
            http_module.LegacyTLSAdapter,
        )

    def test_telegram_uses_news_link_field(self):
        message = telegram_module.format_daily_message(
            [{
                "source": "금융위원회",
                "title": "테스트 기사",
                "summary": "요약: 내용",
                "news_articles": [{
                    "title": "관련 기사",
                    "source": "연합뉴스",
                    "link": "https://example.com/news-link",
                    "summary": "요약",
                }],
                "wp_link": "https://example.com/post",
            }],
            target=__import__("datetime").date(2026, 3, 27),
            session="pm",
        )

        self.assertIn('href="https://example.com/news-link"', message)

    def test_telegram_daily_links_include_referral_params(self):
        message = telegram_module.format_daily_message(
            [{
                "source": "금융위원회",
                "title": "테스트 기사",
                "summary": "요약: 내용",
                "date": "2026-03-27",
                "slug": "007",
                "news_articles": [],
            }],
            target=__import__("datetime").date(2026, 3, 27),
            session="pm",
        )

        self.assertIn('ref=telegram', message)
        self.assertIn('session=pm', message)
        self.assertIn('/articles/2026-03-27/007/', message)

    def test_weekly_loader_preserves_slug(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_data_dir = weekly_analysis_module.DATA_DIR
            weekly_analysis_module.DATA_DIR = Path(tmpdir)
            try:
                (Path(tmpdir) / "2026-03-27.json").write_text(
                    '{"items":[{"slug":"005","source":"금융위원회","title":"테스트","url":"https://example.com","date":"2026-03-27","category":"금융경제","summary":"요약","keywords":["금융"]}]}',
                    encoding="utf-8",
                )
                rows = weekly_analysis_module._load_items_from_json(
                    __import__("datetime").date(2026, 3, 27),
                    __import__("datetime").date(2026, 3, 27),
                )
                self.assertEqual(rows[0]["slug"], "005")
            finally:
                weekly_analysis_module.DATA_DIR = original_data_dir

    def test_subsidy_category_normalization_folds_numeric_codes(self):
        self.assertEqual(subsidy_module._normalize_subsidy_category("2039"), "기타")
        self.assertEqual(subsidy_module._normalize_subsidy_category("멘토링 교육"), "창업교육")


if __name__ == "__main__":
    unittest.main()
