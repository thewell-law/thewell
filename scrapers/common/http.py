"""Polite HTTP client for scrapers.

Wraps httpx with a fixed User-Agent, a retry policy, a per-host minimum
delay between requests, and a robots.txt check. Callers get a thin
fetch() / fetch_text() surface.
"""

from __future__ import annotations

import logging
import threading
import time
import urllib.robotparser
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

USER_AGENT = "The Well Scraper (https://thewell.law; contact@thewell.law)"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MIN_DELAY_SECONDS = 1.0

log = logging.getLogger(__name__)


@dataclass
class FetchResult:
    status: int
    content: bytes
    final_url: str
    content_type: str


class PoliteClient:
    """One-per-scraper HTTP client. Tracks last-fetch time per host and
    enforces a minimum delay; checks robots.txt once per host and caches
    the parser.
    """

    def __init__(
        self,
        user_agent: str = USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT,
        min_delay: float = DEFAULT_MIN_DELAY_SECONDS,
        respect_robots: bool = True,
    ) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
        )
        self._user_agent = user_agent
        self._min_delay = min_delay
        self._respect_robots = respect_robots
        self._last_fetch_at: dict[str, float] = {}
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._lock = threading.Lock()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PoliteClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _sleep_if_needed(self, host: str) -> None:
        with self._lock:
            last = self._last_fetch_at.get(host, 0.0)
            elapsed = time.monotonic() - last
            if elapsed < self._min_delay:
                time.sleep(self._min_delay - elapsed)
            self._last_fetch_at[host] = time.monotonic()

    def _robots_allows(self, url: str) -> bool:
        if not self._respect_robots:
            return True
        parsed = urlparse(url)
        host_key = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._robots_cache.get(host_key)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{host_key}/robots.txt"
            try:
                resp = self._client.get(robots_url)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    rp.parse([])
            except httpx.HTTPError as e:
                log.warning("could not fetch robots.txt at %s: %s", robots_url, e)
                rp.parse([])
            self._robots_cache[host_key] = rp
        return rp.can_fetch(self._user_agent, url)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )
    def fetch(
        self,
        url: str,
        method: str = "GET",
        **kwargs,
    ) -> Optional[FetchResult]:
        """Fetch a URL. Returns None for 404. Raises httpx.HTTPStatusError
        on other 4xx/5xx.
        """
        if not self._robots_allows(url):
            raise RobotsDisallowed(f"robots.txt disallows {url} for {self._user_agent}")
        host = urlparse(url).netloc
        self._sleep_if_needed(host)
        resp = self._client.request(method, url, **kwargs)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return FetchResult(
            status=resp.status_code,
            content=resp.content,
            final_url=str(resp.url),
            content_type=resp.headers.get("content-type", ""),
        )

    def fetch_text(self, url: str, **kwargs) -> Optional[str]:
        result = self.fetch(url, **kwargs)
        if result is None:
            return None
        return result.content.decode(
            _charset_from_content_type(result.content_type),
            errors="replace",
        )


class RobotsDisallowed(RuntimeError):
    """Raised when robots.txt disallows a URL."""


def _charset_from_content_type(ct: str) -> str:
    for part in ct.split(";"):
        part = part.strip().lower()
        if part.startswith("charset="):
            return part.split("=", 1)[1].strip().strip('"')
    return "utf-8"
