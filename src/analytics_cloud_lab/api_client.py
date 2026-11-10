"""Reusable REST client with retries, timeouts and cursor/next-link pagination.

Works with any JSON API that returns pages like:
    {"items": [...], "next": "https://api.example.com/things?cursor=abc"}
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)


class PaginatedAPIClient:
    def __init__(self, base_url: str, token: str | None = None, timeout: float = 10.0,
                 max_retries: int = 3, session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        retry = Retry(total=max_retries, backoff_factor=0.5,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods={"GET"})
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers.setdefault("Accept", "application/json")

    def _url(self, path_or_url: str) -> str:
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url
        return f"{self.base_url}/{path_or_url.lstrip('/')}"

    def get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        resp = self.session.get(self._url(path), params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def iter_items(self, path: str, params: dict | None = None, items_key: str = "items",
                   next_key: str = "next", max_pages: int = 1000) -> Iterator[dict]:
        url, page = path, 0
        while url and page < max_pages:
            data = self.get(url, params if page == 0 else None)
            yield from data.get(items_key, [])
            url = data.get(next_key)
            page += 1
            log.debug("page %s done, next=%s", page, url)
