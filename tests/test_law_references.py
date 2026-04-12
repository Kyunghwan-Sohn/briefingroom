"""법령 참조 관계 추출 테스트."""
from __future__ import annotations

import unittest

from briefingroom.law_references import (
    extract_references_from_article,
    _article_no_str,
)


class ArticleNoStrTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_article_no_str("3"), "3")

    def test_with_sub(self):
        self.assertEqual(_article_no_str("3", "2"), "3의2")

    def test_none_sub(self):
        self.assertEqual(_article_no_str("10", None), "10")


class ExternalReferenceTest(unittest.TestCase):
    def test_quoted_law_reference(self):
        content = '「자본시장과 금융투자업에 관한 법률」 제3조의 금융투자상품에 해당하는'
        refs = extract_references_from_article(
            "test_id", "보험업법", "108", content, {"자본시장과 금융투자업에 관한 법률": "law_001"}
        )
        cross = [r for r in refs if r["ref_type"] == "cross"]
        self.assertTrue(len(cross) >= 1)
        self.assertEqual(cross[0]["target_law_name"], "자본시장과 금융투자업에 관한 법률")
        self.assertEqual(cross[0]["target_article_no"], "3")

    def test_quoted_with_sub_article(self):
        content = '「금융소비자 보호에 관한 법률」 제100조의2에 따라'
        refs = extract_references_from_article(
            "test_id", "자본시장법", "5", content, {"금융소비자 보호에 관한 법률": "law_002"}
        )
        cross = [r for r in refs if r["ref_type"] == "cross"]
        self.assertTrue(len(cross) >= 1)
        self.assertEqual(cross[0]["target_article_no"], "100의2")


class ParentLawReferenceTest(unittest.TestCase):
    def test_decree_references_parent_law(self):
        content = '법 제3조에 따른 금융투자상품의 범위는 다음과 같다'
        refs = extract_references_from_article(
            "test_id", "자본시장과 금융투자업에 관한 법률 시행령", "4", content, {}
        )
        up = [r for r in refs if r["ref_type"] == "up"]
        self.assertTrue(len(up) >= 1)
        self.assertEqual(up[0]["target_law_name"], "자본시장과 금융투자업에 관한 법률")
        self.assertEqual(up[0]["target_article_no"], "3")

    def test_this_law_reference(self):
        content = '이 법 제10조의 규정에 의한 인가를 받은 자'
        refs = extract_references_from_article(
            "test_id", "은행법 시행령", "5", content, {}
        )
        up = [r for r in refs if r["ref_type"] == "up"]
        self.assertTrue(len(up) >= 1)
        self.assertEqual(up[0]["target_article_no"], "10")


class DecreeReferenceTest(unittest.TestCase):
    def test_young_reference(self):
        content = '영 제4조에 따라 세부 범위를 정한다'
        refs = extract_references_from_article(
            "test_id", "금융투자업규정", "1-2", content,
            {"자본시장과 금융투자업에 관한 법률 시행령": "decree_001"}
        )
        up = [r for r in refs if r["ref_type"] == "up"]
        self.assertTrue(len(up) >= 1)
        self.assertIn("시행령", up[0]["target_law_name"])

    def test_decree_keyword(self):
        content = '시행령 제15조에서 정하는 기준'
        refs = extract_references_from_article(
            "test_id", "보험업감독규정", "3", content, {}
        )
        up = [r for r in refs if r["ref_type"] == "up"]
        self.assertTrue(len(up) >= 1)


class NoSelfReferenceTest(unittest.TestCase):
    def test_external_not_self(self):
        content = '「자본시장법」 제3조에 따라'
        refs = extract_references_from_article(
            "test_id", "자본시장법", "10", content, {"자본시장법": "law_001"}
        )
        cross = [r for r in refs if r["ref_type"] == "cross"]
        self.assertEqual(len(cross), 0, "같은 법 참조는 cross가 아님")


if __name__ == "__main__":
    unittest.main()
