"""FreeToGame API extractor."""

from ingestion.http import make_session, polite_get

BASE_URL = "https://www.freetogame.com/api/games"


def fetch_games():
    session = make_session()
    errors = []
    for platform in ("pc", "windows"):
        try:
            response = polite_get(
                session, BASE_URL, params={"platform": platform}
            )
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("FreeToGame returned a non-list response")
            records = []
            for item in payload:
                game_id = item.get("id")
                title = item.get("title")
                if game_id is None or not title:
                    continue
                records.append(
                    {
                        "source": "freetogame",
                        "source_game_id": str(game_id),
                        "title": str(title).strip(),
                        "genre": item.get("genre"),
                        "developer": item.get("developer"),
                        "publisher": item.get("publisher"),
                        "release_date": item.get("release_date") or None,
                        "platform": item.get("platform") or platform,
                        "game_url": item.get("game_url") or item.get("freetogame_profile_url"),
                        "offer": None,
                        "source_payload": item,
                    }
                )
            if records:
                return records
            errors.append(f"platform={platform}: API returned no game records")
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"platform={platform}: {exc}")
        except Exception as exc:
            errors.append(f"platform={platform}: {type(exc).__name__}: {exc}")
    raise RuntimeError("FreeToGame requests failed: " + " | ".join(errors))


def extract_result():
    try:
        records = fetch_games()
        return {
            "source": "freetogame",
            "status": "success" if records else "empty",
            "records": records,
            "count": len(records),
            "error": None,
        }
    except Exception as exc:
        return {
            "source": "freetogame",
            "status": "failed",
            "records": [],
            "count": 0,
            "error": str(exc),
        }
