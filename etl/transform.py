"""Normalize source records and conservatively deduplicate game titles."""

import hashlib
import re
import unicodedata
from datetime import date, datetime

SOURCES = ("freetogame", "cheapshark", "wikipedia")


def normalize_title(title):
    normalized = unicodedata.normalize("NFKD", str(title or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.casefold()
    normalized = re.sub(r"[\W_]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def _year(value):
    if not value:
        return None
    if isinstance(value, (date, datetime)):
        return value.year
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value))
    return int(match.group(1)) if match else None


def _date_value(value):
    if not value:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d %B %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _canonical_keys(records):
    years_by_title = {}
    for record in records:
        title = normalize_title(record.get("title"))
        year = _year(record.get("release_date"))
        if title and year:
            years_by_title.setdefault(title, set()).add(year)
    keys = []
    for record in records:
        title = normalize_title(record.get("title"))
        year = _year(record.get("release_date"))
        known_years = years_by_title.get(title, set())
        if len(known_years) <= 1:
            year = next(iter(known_years), year)
        identity = f"{title}|{year if year else 'undated'}"
        keys.append(hashlib.sha256(identity.encode("utf-8")).hexdigest())
    return keys


def transform_sources(source_results):
    valid_records = []
    for result in source_results:
        if not isinstance(result, dict) or result.get("status") == "failed":
            continue
        source = result.get("source")
        if source not in SOURCES:
            continue
        for item in result.get("records") or []:
            title = str(item.get("title") or "").strip()
            source_game_id = str(item.get("source_game_id") or "").strip()
            if not title or not source_game_id:
                continue
            valid_records.append(
                {
                    "source": source,
                    "source_game_id": source_game_id,
                    "title": title,
                    "normalized_title": normalize_title(title),
                    "genre": _clean(item.get("genre")),
                    "developer": _clean(item.get("developer")),
                    "publisher": _clean(item.get("publisher")),
                    "release_date": _date_value(item.get("release_date")),
                    "platform": _clean(item.get("platform")),
                    "game_url": _clean(item.get("game_url")),
                    "offer": item.get("offer"),
                    "source_payload": item.get("source_payload") or {},
                }
            )
    for record, canonical_key in zip(valid_records, _canonical_keys(valid_records)):
        record["canonical_key"] = canonical_key

    offers = [
        {
            "canonical_key": record["canonical_key"],
            "source": record["source"],
            **record["offer"],
        }
        for record in valid_records
        if record.get("offer")
    ]
    # A source ID is unique within each source; retain the newest duplicate deterministically.
    by_source_id = {}
    for record in valid_records:
        by_source_id[(record["source"], record["source_game_id"])] = record
    records = list(by_source_id.values())

    games_by_key = {}
    for record in records:
        game = games_by_key.setdefault(
            record["canonical_key"],
            {
                "canonical_key": record["canonical_key"],
                "normalized_title": record["normalized_title"],
                "title": record["title"],
                "genre": None,
                "developer": None,
                "publisher": None,
                "release_date": None,
                "platform": None,
                "game_url": None,
                "sources": set(),
            },
        )
        for field in (
            "genre",
            "developer",
            "publisher",
            "release_date",
            "platform",
            "game_url",
        ):
            if not game[field] and record.get(field):
                game[field] = record[field]
        game["sources"].add(record["source"])
    games = list(games_by_key.values())
    for game in games:
        game["sources"] = sorted(game["sources"])
    return {
        "records": records,
        "games": games,
        "offers": offers,
        "source_results": source_results,
        "extracted_count": sum(
            int(result.get("count") or 0)
            for result in source_results
            if isinstance(result, dict)
        ),
    }


def _clean(value):
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None
