"""
base_scraper.py
---------------
Reusable base class for making HTTP requests with a shared
session, default headers, and simple retry/error handling.
"""

import logging
import time
from typing import Optional, Dict, Any

import requests


class BaseScraper:
    """Base class to handle HTTP requests with a persistent session."""

    def __init__(
        self,
        base_url: str = "",
        user_agent: str = "Mozilla/5.0",
        retries: int = 3,
        backoff: float = 1.0,
        timeout: int = 10,
    ) -> None:
        """
        Args:
            base_url: Optional prefix for all relative URLs.
            user_agent: Default User-Agent header.
            retries: Number of times to retry on request failure.
            backoff: Seconds to wait between retries (exponential backoff).
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self.backoff = backoff
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Perform an HTTP request with retries.

        Args:
            method: "GET" or "POST".
            url: Absolute or relative URL.
            **kwargs: Passed to requests.Session.request().

        Returns:
            requests.Response: Successful response.

        Raises:
            requests.HTTPError if all retries fail.
        """
        full_url = f"{self.base_url}{url}" if self.base_url and not url.startswith("http") else url

        for attempt in range(1, self.retries + 1):
            try:
                self.logger.debug("Request %s %s (attempt %d)", method, full_url, attempt)
                resp = self.session.request(method, full_url, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                self.logger.warning("Request failed: %s", e)
                if attempt == self.retries:
                    self.logger.error("All retries failed for %s", full_url)
                    raise
                time.sleep(self.backoff * attempt)  # simple exponential backoff

    # Convenience wrappers ---------------------------------------------
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> requests.Response:
        return self._request("GET", url, params=params, **kwargs)

    def post(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> requests.Response:
        return self._request("POST", url, data=data, **kwargs)
