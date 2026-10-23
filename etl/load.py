"""Idempotent PostgreSQL UPSERT operations."""

import json
import os
from contextlib import closing

import psycopg2
from psycopg2.extras import Json

def get_connection():
    return psycopg2.connect(
        host=os.getenv("ANALYTICS_DB_HOST", "localhost"),
        port=int(os.getenv("ANALYTICS_DB_PORT", "5453")),
        dbname=os.getenv("ANALYTICS_DB_NAME", "game_analytics"),
        user=os.getenv("ANALYTICS_DB_USER", "game_analytics"),
        password=os.getenv("ANALYTICS_DB_PASSWORD", ""),
        connect_timeout=10,
        application_name="pc-game-analytics",
    )


def load_transformed(transformed):
    records = transformed.get("records") or []
    games = transformed.get("games") or []
    offers = transformed.get("offers") or []
    with closing(get_connection()) as connection:
        with connection:
            with connection.cursor() as cursor:
                for game in games:
                    cursor.execute(
                        """
                        INSERT INTO games (
                            canonical_key, normalized_title, title, genre, developer,
                            publisher, release_date, platform, game_url, last_seen_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (canonical_key) DO UPDATE SET
                            normalized_title = EXCLUDED.normalized_title,
                            title = EXCLUDED.title,
                            genre = COALESCE(EXCLUDED.genre, games.genre),
                            developer = COALESCE(EXCLUDED.developer, games.developer),
                            publisher = COALESCE(EXCLUDED.publisher, games.publisher),
                            release_date = COALESCE(EXCLUDED.release_date, games.release_date),
                            platform = COALESCE(EXCLUDED.platform, games.platform),
                            game_url = COALESCE(EXCLUDED.game_url, games.game_url),
                            last_seen_at = NOW()
                        """,
                        (
                            game["canonical_key"],
                            game["normalized_title"],
                            game["title"],
                            game.get("genre"),
                            game.get("developer"),
                            game.get("publisher"),
                            game.get("release_date"),
                            game.get("platform"),
                            game.get("game_url"),
                        ),
                    )
                for record in records:
                    cursor.execute(
                        """
                        INSERT INTO raw_games (
                            source, source_game_id, canonical_key, title,
                            normalized_title, genre, developer, publisher,
                            release_date, platform, game_url, source_payload, fetched_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (source, source_game_id) DO UPDATE SET
                            canonical_key = EXCLUDED.canonical_key,
                            title = EXCLUDED.title,
                            normalized_title = EXCLUDED.normalized_title,
                            genre = COALESCE(EXCLUDED.genre, raw_games.genre),
                            developer = COALESCE(EXCLUDED.developer, raw_games.developer),
                            publisher = COALESCE(EXCLUDED.publisher, raw_games.publisher),
                            release_date = COALESCE(EXCLUDED.release_date, raw_games.release_date),
                            platform = COALESCE(EXCLUDED.platform, raw_games.platform),
                            game_url = COALESCE(EXCLUDED.game_url, raw_games.game_url),
                            source_payload = EXCLUDED.source_payload,
                            fetched_at = NOW()
                        """,
                        (
                            record["source"],
                            record["source_game_id"],
                            record["canonical_key"],
                            record["title"],
                            record["normalized_title"],
                            record.get("genre"),
                            record.get("developer"),
                            record.get("publisher"),
                            record.get("release_date"),
                            record.get("platform"),
                            record.get("game_url"),
                            Json(record.get("source_payload") or {}),
                        ),
                    )
                for offer in offers:
                    cursor.execute(
                        """
                        INSERT INTO game_offers (
                            game_id, source, source_offer_id, store_name, currency,
                            normal_price, sale_price, discount_percent, deal_rating,
                            offer_url, fetched_at
                        )
                        SELECT id, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                        FROM games WHERE canonical_key = %s
                        ON CONFLICT (source, source_offer_id) DO UPDATE SET
                            game_id = EXCLUDED.game_id,
                            store_name = EXCLUDED.store_name,
                            currency = EXCLUDED.currency,
                            normal_price = EXCLUDED.normal_price,
                            sale_price = EXCLUDED.sale_price,
                            discount_percent = EXCLUDED.discount_percent,
                            deal_rating = EXCLUDED.deal_rating,
                            offer_url = EXCLUDED.offer_url,
                            fetched_at = NOW()
                        """,
                        (
                            offer["source"],
                            offer["source_offer_id"],
                            offer.get("store_name"),
                            offer.get("currency") or "USD",
                            offer.get("normal_price"),
                            offer.get("sale_price"),
                            offer.get("discount_percent"),
                            offer.get("deal_rating"),
                            offer.get("offer_url"),
                            offer["canonical_key"],
                        ),
                    )
                cursor.execute("SELECT COUNT(*) FROM games")
                total_games = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM raw_games")
                total_raw = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM game_offers")
                total_offers = cursor.fetchone()[0]
    return {
        "loaded_records": len(records),
        "normalized_games": len(games),
        "offers_loaded": len(offers),
        "total_games": total_games,
        "total_raw_records": total_raw,
        "total_offers": total_offers,
    }


def record_pipeline_run(run_id, dag_id, status, started_at, metrics, source_results, quality, error_summary):
    with closing(get_connection()) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO pipeline_runs (
                        run_id, dag_id, status, started_at, finished_at,
                        records_extracted, records_loaded, failed_sources,
                        quality_passed, error_summary
                    ) VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        finished_at = NOW(),
                        records_extracted = EXCLUDED.records_extracted,
                        records_loaded = EXCLUDED.records_loaded,
                        failed_sources = EXCLUDED.failed_sources,
                        quality_passed = EXCLUDED.quality_passed,
                        error_summary = EXCLUDED.error_summary
                    """,
                    (
                        run_id,
                        dag_id,
                        status,
                        started_at,
                        metrics.get("extracted_count", 0),
                        metrics.get("loaded_records", 0),
                        sum(
                            1
                            for result in source_results
                            if result.get("status") == "failed"
                        ),
                        bool(quality.get("passed")),
                        error_summary,
                    ),
                )
                for result in source_results:
                    cursor.execute(
                        """
                        INSERT INTO pipeline_source_runs (
                            run_id, source, status, records_extracted, error_message
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (run_id, source) DO UPDATE SET
                            status = EXCLUDED.status,
                            records_extracted = EXCLUDED.records_extracted,
                            error_message = EXCLUDED.error_message
                        """,
                        (
                            run_id,
                            result["source"],
                            result["status"],
                            result.get("count", 0),
                            result.get("error"),
                        ),
                    )
