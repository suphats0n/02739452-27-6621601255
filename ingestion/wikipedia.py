"""Robots-aware Wikipedia table extractor using requests and BeautifulSoup."""

import re
import time
from copy import deepcopy
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from ingestion.http import USER_AGENT, make_session, polite_get

PRIMARY_URL = "https://en.wikipedia.org/wiki/List_of_free_PC_games"
FALLBACK_URLS = (
    "https://en.wikipedia.org/wiki/List_of_computer_role-playing_games",
)


def _robots_parser(session, url):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    response = polite_get(session, robots_url)
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())
    return parser


def _cell_text(cell):
    cleaned = deepcopy(cell)
    for citation in cleaned.select("sup.reference, sup.noprint"):
        citation.decompose()
    return re.sub(r"\s+", " ", cleaned.get_text(" ", strip=True)).strip()


def _extract_table_records(html, url):
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for table_index, table in enumerate(soup.select("table.wikitable")):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [
            _cell_text(cell).lower()
            for cell in rows[0].find_all(["th", "td"], recursive=False)
        ]
        name_index = next(
            (
                index
                for index, header in enumerate(headers)
                if any(term in header for term in ("game", "title", "name"))
            ),
            None,
        )
        if name_index is None:
            continue
        for row_index, row in enumerate(rows[1:], start=1):
            cells = row.find_all(["th", "td"], recursive=False)
            if name_index >= len(cells):
                continue
            title = _cell_text(cells[name_index])
            if not title or title.lower() in {"tba", "n/a", "unknown", "—", "-"}:
                continue
            values = {
                header: _cell_text(cells[index])
                for index, header in enumerate(headers)
                if index < len(cells) and header
            }
            link = cells[name_index].find("a", href=True)
            game_url = None
            if link:
                href = link["href"]
                game_url = (
                    f"https://en.wikipedia.org{href}"
                    if href.startswith("/")
                    else href
                )
            platform = next(
                (
                    value
                    for key, value in values.items()
                    if "platform" in key or "operating system" in key
                ),
                None,
            )
            if not platform and url == PRIMARY_URL:
                platform = "PC"
            if url != PRIMARY_URL and platform and not re.search(
                r"\b(windows|linux|mac(?:intosh)?|mac os|dos|pc)\b",
                platform,
                flags=re.IGNORECASE,
            ):
                continue
            records.append(
                {
                    "source": "wikipedia",
                    "source_game_id": f"{url}#table-{table_index}-row-{row_index}",
                    "title": title,
                    "genre": next(
                        (value for key, value in values.items() if "genre" in key),
                        None,
                    ),
                    "developer": next(
                        (
                            value
                            for key, value in values.items()
                            if "developer" in key or "studio" in key
                        ),
                        None,
                    ),
                    "publisher": next(
                        (value for key, value in values.items() if "publisher" in key),
                        None,
                    ),
                    "release_date": next(
                        (
                            value
                            for key, value in values.items()
                            if "release" in key or "year" in key
                        ),
                        None,
                    ),
                    "platform": platform,
                    "game_url": game_url or url,
                    "offer": None,
                    "source_payload": {"table_values": values, "page_url": url},
                }
            )
    return records


def fetch_games():
    session = make_session()
    candidates = (PRIMARY_URL,) + FALLBACK_URLS
    robots_by_origin = {}
    errors = []
    for url in candidates:
        try:
            origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt"
            if origin not in robots_by_origin:
                robots_by_origin[origin] = _robots_parser(session, url)
            if not robots_by_origin[origin].can_fetch(USER_AGENT, url):
                raise PermissionError(f"robots.txt disallows scraping {url}")
            response = polite_get(session, url)
            records = _extract_table_records(response.text, url)
            if records:
                return records
            errors.append(f"{url}: no game rows found in HTML tables")
        except Exception as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
        time.sleep(1)
    raise RuntimeError("No permitted Wikipedia game table was available: " + " | ".join(errors))


def extract_result():
    try:
        records = fetch_games()
        return {
            "source": "wikipedia",
            "status": "success" if records else "empty",
            "records": records,
            "count": len(records),
            "error": None,
        }
    except Exception as exc:
        return {
            "source": "wikipedia",
            "status": "failed",
            "records": [],
            "count": 0,
            "error": str(exc),
        }
