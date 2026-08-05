"""Core calculation tests that run without starting the Streamlit server."""

from __future__ import annotations

import unittest

import pandas as pd

from src.config import CROP_MODULE, LIVESTOCK_MODULE, SOURCE_COLUMNS
from src.data import apply_filters, prepare_dataframe, production_frame
from src.formatting import compact_number
from src.metrics import cooccurrence_pairs, quality_summary


def sample_source() -> pd.DataFrame:
    """Create a minimal source-shaped dataframe for deterministic tests."""
    defaults = {column: [None, None, None] for column in SOURCE_COLUMNS}
    defaults.update(
        {
            "asset_type": ["crop", "intercrop", "crop"],
            "asset_name": ["maize", "beans + maize", "coffee"],
            "query": ["Plant maize", "Beans & maize", "Plant coffee"],
            "query_original": ["Plant maize", "Beans & maize", "Plant coffee"],
            "user_country": ["Kenya", "Kenya", "Kenya"],
            "user_geo_level2": ["Nyeri", None, "Nakuru"],
            "query_year_month": ["2025-03", "2026-10", "2024-11"],
            "language": ["en", "en", "en"],
            "intercrop_components": [None, "beans + maize", None],
            "value_chain": ["maize", "beans + maize", "coffee"],
            "clean_asset_type": ["crop", "intercrop", "crop"],
            "query_cleaning_changed": [False, False, False],
            "query_is_garbled": [False, False, False],
            "query_word_count": [2, 3, 2],
            "query_duplicate_count": [2, 1, 1],
            "is_duplicate_query": [True, False, False],
            "crop_review_flag": [False, False, False],
            "crop_review_status": ["crop query", "crop query", "crop query"],
            "classification_status": [
                "primary_intent_only",
                "domain_only",
                "primary_intent_only",
            ],
            "primary_domain": ["Crop Planning", "Crop Planning", "Crop Management"],
            "primary_subdomain": [
                "Crop calendars and seasonal planning",
                None,
                "Soil fertility management",
            ],
            "primary_intent_id": ["INT-005", None, "INT-072"],
            "primary_farmer_intent": [
                "Determine the appropriate planting period",
                None,
                "Select fertilizer for an established crop",
            ],
            "primary_intent_score": [1.0, 0.0, 1.0],
            "primary_match_evidence": ["plant", None, "fertilizer"],
            "secondary_intent_score": [None, None, None],
            "matched_intent_count": [1, 0, 1],
            "domain_confidence": ["high", "no_match", "high"],
            "domain_review_flag": [False, True, False],
            "domain_review_reason": [None, "No accepted intent", None],
        }
    )
    return pd.DataFrame(defaults)


def sample_livestock_source() -> pd.DataFrame:
    """Create a minimal approved livestock-shaped dataframe."""
    defaults = {
        column: [None, None, None] for column in LIVESTOCK_MODULE.source_columns
    }
    defaults.update(
        {
            "asset_type": ["livestock", "mixed_livestock", "livestock"],
            "asset_name": ["cattle", "goat + sheep", "chicken"],
            "query": ["Feed cattle", "Keep goats and sheep", "Vaccinate chicken"],
            "query_original": [
                "Feed cattle",
                "Keep goats and sheep",
                "Vaccinate chicken",
            ],
            "user_country": ["Kenya", "Kenya", "Kenya"],
            "user_geo_level2": ["Nyeri", None, "Kiambu"],
            "query_year_month": ["2025-03", "2026-10", "2024-11"],
            "language": ["en", "en", "en"],
            "mixed_livestock_components": [None, "goat + sheep", None],
            "value_chain": ["cattle", "goat + sheep", "chicken"],
            "clean_asset_type": ["livestock", "mixed_livestock", "livestock"],
            "query_cleaning_changed": [False, False, False],
            "query_is_garbled": [False, False, False],
            "query_word_count": [2, 4, 2],
            "query_duplicate_count": [2, 1, 1],
            "is_duplicate_query": [True, False, False],
            "livestock_review_flag": [False, True, False],
            "livestock_review_status": [
                "livestock query",
                "animal/pet/non-conventional livestock value chain",
                "livestock query",
            ],
            "classification_status": [
                "primary_intent_only",
                "domain_only",
                "primary_intent_only",
            ],
            "primary_domain": [
                "Livestock Management",
                "Livestock Planning",
                "Livestock Management",
            ],
            "primary_subdomain": [
                "Feeding management",
                None,
                "Vaccination and preventive treatment",
            ],
            "primary_intent_id": ["LIV-001", None, "LIV-002"],
            "primary_farmer_intent": [
                "Select feed",
                None,
                "Develop a vaccination schedule",
            ],
            "primary_intent_score": [1.0, 0.0, 1.0],
            "primary_match_evidence": ["feed", None, "vaccinate"],
            "secondary_intent_score": [None, None, None],
            "matched_intent_count": [1, 0, 1],
            "domain_confidence": ["high", "no_match", "high"],
            "domain_review_flag": [False, True, False],
            "domain_review_reason": [None, "No accepted intent", None],
        }
    )
    return pd.DataFrame(defaults)


class DashboardCoreTests(unittest.TestCase):
    def test_compact_number(self) -> None:
        self.assertEqual(compact_number(1_200), "1.2K")
        self.assertEqual(compact_number(420_000), "420K")
        self.assertEqual(compact_number(1_300_000), "1.3M")

    def test_production_year_exclusion(self) -> None:
        prepared = prepare_dataframe(sample_source())
        production = production_frame(prepared)
        self.assertEqual(set(production["year"].astype(int)), {2025, 2026})
        self.assertEqual(len(production), 2)

    def test_quality_reconciliation(self) -> None:
        prepared = production_frame(prepare_dataframe(sample_source()))
        summary = quality_summary(prepared)
        self.assertEqual(summary["unique_rows"], 2)
        self.assertEqual(summary["original_occurrences"], 3)
        self.assertEqual(summary["duplicate_occurrences"], 1)
        self.assertEqual(summary["missing_county"], 1)

    def test_intercrop_pair(self) -> None:
        prepared = production_frame(prepare_dataframe(sample_source()))
        pairs = cooccurrence_pairs(prepared)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs.iloc[0]["Source"], "beans")
        self.assertEqual(pairs.iloc[0]["Target"], "maize")

    def test_livestock_module_preparation_and_filters(self) -> None:
        prepared = production_frame(
            prepare_dataframe(sample_livestock_source(), LIVESTOCK_MODULE)
        )
        self.assertEqual(
            set(prepared["asset_type_label"]),
            {"Single livestock", "Mixed livestock"},
        )
        pairs = cooccurrence_pairs(
            prepared,
            mixed_asset_label=LIVESTOCK_MODULE.mixed_asset_label,
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs.iloc[0]["Source"], "goat")
        self.assertEqual(pairs.iloc[0]["Target"], "sheep")

        filtered = apply_filters(
            prepared,
            {
                "asset_types": ["Single livestock"],
                "confidence_levels": ["High"],
            },
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]["value_chain_label"], "cattle")

    def test_module_schemas_match_approved_variants(self) -> None:
        self.assertIn("intercrop_components", CROP_MODULE.source_columns)
        self.assertIn("mixed_livestock_components", LIVESTOCK_MODULE.source_columns)
        self.assertNotIn("crop_review_flag", LIVESTOCK_MODULE.source_columns)


if __name__ == "__main__":
    unittest.main()
