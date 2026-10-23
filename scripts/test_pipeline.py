"""Local end-to-end ETL check, including graceful source failure and quality branching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etl.quality import validate_data_quality
from etl.transform import transform_sources
from ingestion.cheapshark import extract_result as extract_cheapshark
from ingestion.freetogame import extract_result as extract_freetogame
from ingestion.wikipedia import extract_result as extract_wikipedia


def main():
    results = [extract_freetogame(), extract_cheapshark(), extract_wikipedia()]
    transformed = transform_sources(results)
    quality = validate_data_quality(transformed, minimum_valid_records=100)
    print(
        "Source states:",
        {result["source"]: (result["status"], result["count"]) for result in results},
    )
    print("Quality check:", quality)
    failed_source = {
        "source": "wikipedia",
        "status": "failed",
        "count": 0,
        "records": [],
        "error": "intentional fault-tolerance check",
    }
    partial = transform_sources([results[0], results[1], failed_source])
    if len(partial["records"]) >= 100 and not validate_data_quality(
        partial, minimum_valid_records=100
    )["passed"]:
        raise AssertionError("A failed source prevented valid sources from passing quality")
    rejected = validate_data_quality({"records": [], "games": []})
    if rejected["passed"]:
        raise AssertionError("Empty data unexpectedly passed quality")
    print("Source-failure tolerance and quality accept/reject branches: OK")
    if not quality["passed"]:
        raise SystemExit("Real source data failed validation; inspect source availability.")


if __name__ == "__main__":
    main()
