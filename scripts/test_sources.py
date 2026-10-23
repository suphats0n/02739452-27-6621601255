"""Live integration smoke test for the three public data sources."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.cheapshark import fetch_deals
from ingestion.freetogame import fetch_games as fetch_free_games
from ingestion.wikipedia import fetch_games as fetch_wikipedia_games


def main():
    checks = (
        ("FreeToGame", fetch_free_games),
        ("CheapShark", fetch_deals),
        ("Wikipedia", fetch_wikipedia_games),
    )
    total = 0
    failures = []
    for name, fetch in checks:
        try:
            records = fetch()
            print(f"{name}: {len(records)} live records")
            if not records:
                failures.append(f"{name} returned no records")
            total += len(records)
        except Exception as exc:
            print(f"{name}: ERROR: {type(exc).__name__}: {exc}")
            failures.append(f"{name}: {exc}")
    print(f"Combined live records: {total}")
    if total < 100:
        failures.append(f"Expected at least 100 records across sources; got {total}")
    if failures:
        raise SystemExit("\n".join(failures))


if __name__ == "__main__":
    main()
