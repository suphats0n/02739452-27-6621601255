"""Data-quality gates used by the Airflow branch and local tests."""


def validate_data_quality(transformed, minimum_valid_records=1):
    records = transformed.get("records") or []
    games = transformed.get("games") or []
    errors = []
    if len(records) < minimum_valid_records:
        errors.append(
            f"Expected at least {minimum_valid_records} valid source records; got {len(records)}."
        )
    if not games:
        errors.append("No normalized games are available.")
    for index, record in enumerate(records):
        for field in ("source", "source_game_id", "title", "normalized_title", "canonical_key"):
            if not record.get(field):
                errors.append(f"Record {index} is missing required field '{field}'.")
                break
        offer = record.get("offer")
        if offer:
            for field in ("normal_price", "sale_price"):
                value = offer.get(field)
                if value is not None:
                    try:
                        if float(value) < 0:
                            errors.append(f"Record {index} has a negative {field}.")
                    except (TypeError, ValueError):
                        errors.append(f"Record {index} has a non-numeric {field}.")
            discount = offer.get("discount_percent")
            if discount is not None:
                try:
                    if not 0 <= float(discount) <= 100:
                        errors.append(f"Record {index} has a discount outside 0-100%.")
                except (TypeError, ValueError):
                    errors.append(f"Record {index} has a non-numeric discount.")
    if len({(r["source"], r["source_game_id"]) for r in records}) != len(records):
        errors.append("Duplicate (source, source_game_id) values remain after transformation.")
    return {
        "passed": not errors,
        "valid_records": len(records),
        "normalized_games": len(games),
        "errors": errors,
    }
