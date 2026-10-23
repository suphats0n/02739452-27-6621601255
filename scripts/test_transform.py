"""Offline unit tests for normalization, deduplication, and quality validation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etl.quality import validate_data_quality
from etl.transform import normalize_title, transform_sources


class TransformTests(unittest.TestCase):
    def test_title_normalization(self):
        self.assertEqual(normalize_title("Call_of_Duty: Black Ops"), "call of duty black ops")

    def test_deduplicates_unknown_year_and_preserves_each_offer(self):
        sources = [
            {
                "source": "freetogame",
                "status": "success",
                "records": [
                    {
                        "source": "freetogame",
                        "source_game_id": "ftg-1",
                        "title": "Same Game!",
                        "release_date": "2020-01-01",
                    }
                ],
            },
            {
                "source": "cheapshark",
                "status": "success",
                "records": [
                    {
                        "source": "cheapshark",
                        "source_game_id": "deal-game",
                        "title": "same game",
                        "offer": {"source_offer_id": "deal-1", "sale_price": 2.5},
                    },
                    {
                        "source": "cheapshark",
                        "source_game_id": "deal-game",
                        "title": "same game",
                        "offer": {"source_offer_id": "deal-2", "sale_price": 3.5},
                    },
                ],
            },
            {
                "source": "wikipedia",
                "status": "failed",
                "records": [],
                "error": "intentional unit-test failure",
            },
        ]

        transformed = transform_sources(sources)

        self.assertEqual(len(transformed["games"]), 1)
        self.assertEqual(len(transformed["records"]), 2)
        self.assertEqual(len(transformed["offers"]), 2)
        self.assertTrue(validate_data_quality(transformed)["passed"])

    def test_conflicting_release_years_are_not_merged(self):
        records = [
            {
                "source": "freetogame",
                "status": "success",
                "records": [
                    {
                        "source": "freetogame",
                        "source_game_id": "one",
                        "title": "Same Title",
                        "release_date": "2010-01-01",
                    },
                    {
                        "source": "freetogame",
                        "source_game_id": "two",
                        "title": "Same Title",
                        "release_date": "2020-01-01",
                    },
                ],
            }
        ]
        self.assertEqual(len(transform_sources(records)["games"]), 2)

    def test_rejects_empty_data_and_invalid_prices(self):
        self.assertFalse(validate_data_quality({"records": [], "games": []})["passed"])
        transformed = transform_sources(
            [
                {
                    "source": "cheapshark",
                    "status": "success",
                    "records": [
                        {
                            "source": "cheapshark",
                            "source_game_id": "bad-price",
                            "title": "Test",
                            "offer": {
                                "source_offer_id": "bad-price",
                                "sale_price": -1,
                            },
                        }
                    ],
                }
            ]
        )
        self.assertFalse(validate_data_quality(transformed)["passed"])


if __name__ == "__main__":
    unittest.main()
