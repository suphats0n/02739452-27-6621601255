"""Shared, polite HTTP client settings for public data sources."""

import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = os.getenv(
    "PCGA_USER_AGENT",
    "PCGameAnalyticsExam/1.0 (educational project; contact: student@example.invalid)",
)
REQUEST_TIMEOUT = (5, 25)
REQUEST_DELAY_SECONDS = float(os.getenv("SOURCE_REQUEST_DELAY_SECONDS", "0.5"))
_last_request_at = 0.0


def make_session():
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(
        {"User-Agent": USER_AGENT, "Accept": "application/json, text/html;q=0.9"}
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def polite_get(session, url, **kwargs):
    global _last_request_at
    wait = REQUEST_DELAY_SECONDS - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    response = session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
    _last_request_at = time.monotonic()
    response.raise_for_status()
    return response
