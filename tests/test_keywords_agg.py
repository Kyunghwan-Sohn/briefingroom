"""키워드 집계 파이프라인 테스트."""
from __future__ import annotations

import unittest
from datetime import date

from briefingroom import keywords_agg


class NormalizationTest(unittest.TestCase):
    def test_dedupe_key_removes_whitespace_and_lowercases(self):
        self.assertEqual(
            keywords_agg._dedupe_key("중동 전쟁"),
            keywords_agg._dedupe_key("중동전쟁"),
        )

    def test_ai_merges_into_인공지능(self):
        self.assertEqual(keywords_agg._dedupe_key("AI"), "인공지능")
        self.assertEqual(keywords_agg._dedupe_key("ai"), "인공지능")
        self.assertEqual(keywords_agg._dedupe_key("인공지능"), "인공지능")


class NoiseFilterTest(unittest.TestCase):
    def test_year_only_is_noise(self):
        self.assertTrue(keywords_agg._is_noise("2026년", "2026년"))
        self.assertTrue(keywords_agg._is_noise("2026", "2026"))

    def test_date_pattern_is_noise(self):
        self.assertTrue(keywords_agg._is_noise("2026년 4월", "2026년4월"))
        self.assertTrue(keywords_agg._is_noise("4월", "4월"))
        self.assertTrue(keywords_agg._is_noise("12월 25일", "12월25일"))

    def test_event_words_are_noise(self):
        for w in ("간담회", "업무협약", "현장점검", "임명"):
            self.assertTrue(keywords_agg._is_noise(w, w))

    def test_real_keywords_are_not_noise(self):
        for w in ("인공지능", "소상공인", "탄소중립", "디지털 전환"):
            key = keywords_agg._dedupe_key(w)
            self.assertFalse(keywords_agg._is_noise(w, key), w)


class ExtractKeywordsTest(unittest.TestCase):
    def test_ministry_names_are_filtered(self):
        item = {"keywords": ["외교부", "기재부", "금융위", "소상공인"]}
        result = keywords_agg._extract_keywords(item)
        displays = [d for _, d in result]
        self.assertNotIn("외교부", displays)
        self.assertNotIn("기재부", displays)
        self.assertNotIn("금융위", displays)
        self.assertIn("소상공인", displays)

    def test_handles_string_keywords_field(self):
        # 구버전 호환: 콤마 join된 문자열
        item = {"keywords": "인공지능, 소상공인, 외교부"}
        result = keywords_agg._extract_keywords(item)
        displays = [d for _, d in result]
        self.assertIn("인공지능", displays)
        self.assertIn("소상공인", displays)
        self.assertNotIn("외교부", displays)

    def test_variants_share_same_dedupe_key(self):
        item = {"keywords": ["중동전쟁", "중동 전쟁", "AI", "인공지능"]}
        result = keywords_agg._extract_keywords(item)
        keys = [k for k, _ in result]
        # 같은 키는 하나로 dedupe되지 않음 (keyword당 1회 등장 인정)
        # 하지만 aggregate 호출 시 동일 key로 집계됨
        self.assertEqual(
            keywords_agg._dedupe_key("중동전쟁"),
            keywords_agg._dedupe_key("중동 전쟁"),
        )
        self.assertEqual(
            keywords_agg._dedupe_key("AI"),
            keywords_agg._dedupe_key("인공지능"),
        )


class AggregateTest(unittest.TestCase):
    def test_aggregate_returns_expected_shape(self):
        result = keywords_agg.aggregate(7)
        self.assertIn("period", result)
        self.assertIn("top", result)
        self.assertIn("by_category", result)
        self.assertIn("category_totals", result)
        self.assertIsInstance(result["top"], list)
        self.assertIsInstance(result["by_category"], dict)

    def test_top_items_respect_min_count(self):
        result = keywords_agg.aggregate(30)
        for item in result["top"]:
            self.assertGreaterEqual(item["count"], keywords_agg.MIN_COUNT)

    def test_top_sorted_descending(self):
        result = keywords_agg.aggregate(30)
        counts = [x["count"] for x in result["top"]]
        self.assertEqual(counts, sorted(counts, reverse=True))


if __name__ == "__main__":
    unittest.main()
