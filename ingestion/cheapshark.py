"""CheapShark PC deal extractor."""

from ingestion.http import make_session, polite_get

DEALS_URL = "https://www.cheapshark.com/api/1.0/deals"
STORES_URL = "https://www.cheapshark.com/api/1.0/stores"
PAGE_SIZE = 60
MAX_PAGES = 3


def _optional_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def fetch_deals():
    session = make_session()
    stores_payload = polite_get(session, STORES_URL).json()
    stores = {
        str(store.get("storeID")): store.get("storeName")
        for store in stores_payload
        if store.get("storeID") is not None
    }
    records = []
    for page in range(MAX_PAGES):
        payload = polite_get(
            session,
            DEALS_URL,
            params={"pageSize": PAGE_SIZE, "pageNumber": page},
        ).json()
        if not isinstance(payload, list):
            raise ValueError("CheapShark returned a non-list deals response")
        if not payload:
            break
        for item in payload:
            game_id = item.get("gameID")
            deal_id = item.get("dealID")
            title = item.get("title")
            if game_id is None or deal_id is None or not title:
                continue
            normal_price = _optional_float(item.get("normalPrice"))
            sale_price = _optional_float(item.get("salePrice"))
            savings = _optional_float(item.get("savings"))
            records.append(
                {
                    "source": "cheapshark",
                    "source_game_id": str(game_id),
                    "title": str(title).strip(),
                    "genre": None,
                    "developer": None,
                    "publisher": None,
                    "release_date": None,
                    "platform": "PC",
                    "game_url": (
                        f"https://www.cheapshark.com/redirect?dealID={deal_id}"
                    ),
                    "offer": {
                        "source_offer_id": str(deal_id),
                        "store_name": stores.get(str(item.get("storeID"))),
                        "currency": "USD",
                        "normal_price": normal_price,
                        "sale_price": sale_price,
                        "discount_percent": round(savings, 2) if savings is not None else None,
                        "deal_rating": _optional_float(item.get("dealRating")),
                        "offer_url": (
                            f"https://www.cheapshark.com/redirect?dealID={deal_id}"
                        ),
                    },
                    "source_payload": item,
                }
            )
        if len(payload) < PAGE_SIZE:
            break
    return records


def extract_result():
    try:
        records = fetch_deals()
        return {
            "source": "cheapshark",
            "status": "success" if records else "empty",
            "records": records,
            "count": len(records),
            "error": None,
        }
    except Exception as exc:
        return {
            "source": "cheapshark",
            "status": "failed",
            "records": [],
            "count": 0,
            "error": str(exc),
        }
