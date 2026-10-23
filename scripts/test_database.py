"""Database schema and idempotent UPSERT integration test."""

import os
import sys
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2
from etl.load import get_connection, load_transformed
from etl.quality import validate_data_quality
from etl.transform import transform_sources


def main():
    fixture_id = "db-test-" + uuid4().hex
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('games', 'raw_games', 'game_offers', 'pipeline_runs')
                """
            )
            tables = {row[0] for row in cursor.fetchall()}
            expected = {"games", "raw_games", "game_offers", "pipeline_runs"}
            if tables != expected:
                raise AssertionError(f"Missing database tables: {expected - tables}")

    fixture = {
        "source_results": [
            {
                "source": "freetogame",
                "status": "success",
                "count": 1,
                "records": [
                    {
                        "source": "freetogame",
                        "source_game_id": fixture_id,
                        "title": fixture_id,
                        "genre": "Test",
                        "platform": "PC",
                        "source_payload": {"integration_test": True},
                        "offer": {
                            "source_offer_id": fixture_id,
                            "normal_price": 10,
                            "sale_price": 5,
                            "discount_percent": 50,
                            "currency": "USD",
                        },
                    }
                ],
            }
        ]
    }
    transformed = transform_sources(fixture["source_results"])
    result = load_transformed(transformed)
    first_count = result["total_raw_records"]
    second_result = load_transformed(transformed)
    if first_count != second_result["total_raw_records"]:
        raise AssertionError("Rerunning the same UPSERT changed the raw row count")
    if second_result["loaded_records"] != 1:
        raise AssertionError("The repeated UPSERT did not update the existing record")
    for key in ("total_games", "total_raw_records", "total_offers"):
        assert result[key] == second_result[key], f"Repeated UPSERT changed {key}"
    transformed["offers"][0]["sale_price"] = 4
    transformed["offers"][0]["discount_percent"] = 60
    transformed["games"][0]["genre"] = "Updated Test"
    transformed["records"][0]["genre"] = "Updated Test"
    updated = load_transformed(transformed)
    for key in ("total_games", "total_raw_records", "total_offers"):
        assert result[key] == updated[key], f"Updating existing values changed {key}"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT g.genre, r.genre, o.sale_price FROM games g "
                "JOIN raw_games r ON r.canonical_key = g.canonical_key "
                "JOIN game_offers o ON o.game_id = g.id WHERE r.source_game_id = %s",
                (fixture_id,),
            )
            assert cursor.fetchone() == ("Updated Test", "Updated Test", 4)
    print("UPSERT insert, repeat, update: games/raw_games/game_offers all OK")
    print(f"Database schema OK; repeated UPSERT stable at {first_count} raw records")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM raw_games WHERE source = %s AND source_game_id = %s",
                ("freetogame", fixture_id),
            )
            cursor.execute("DELETE FROM games WHERE canonical_key = %s", (transformed["games"][0]["canonical_key"],))
        connection.commit()


if __name__ == "__main__":
    main()
