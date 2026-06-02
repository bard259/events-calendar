"""Minimal, dependency-free HTTP client that records rate-limit and ToS signals.

Wraps urllib so the whole pipeline stays on the Python standard library. Every
request updates a CollectorReport so the final report can show, per collector:
  - how many HTTP requests were made
  - whether the source rate-limited us (HTTP 429 / 403 + Retry-After)
  - Terms-of-Service signals (robots.txt disallow, required User-Agent, 403 blocks)
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlparse

from config import USER_AGENT, HTTP_TIMEOUT, DEFAULT_RATE_DELAY
from models import CollectorReport


class HttpClient:
    def __init__(self, report: CollectorReport, rate_delay: float = DEFAULT_RATE_DELAY):
        self.report = report
        self.rate_delay = rate_delay
        self._last_request_ts = 0.0
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    # -- politeness -----------------------------------------------------------
    def _throttle(self):
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.rate_delay:
            time.sleep(self.rate_delay - elapsed)
        self._last_request_ts = time.monotonic()

    def _robots_allows(self, url: str) -> bool:
        """Check robots.txt and obey an explicit Disallow (recorded as a ToS issue).

        We fetch robots.txt *with our declared User-Agent*. Many hosts 403 the default
        Python UA, and the stdlib parser then treats that as "disallow everything" —
        which is wrong. So if robots.txt is missing/blocked/unparseable we treat the
        path as allowed and leave a note, only blocking on an explicit Disallow.
        """
        parts = urlparse(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots_cache:
            self._robots_cache[origin] = self._load_robots(origin)
        rp = self._robots_cache[origin]
        if rp is None:
            return True  # no usable robots.txt -> allowed
        allowed = rp.can_fetch(USER_AGENT, url)
        if not allowed:
            msg = f"robots.txt disallows fetching {url}"
            if msg not in self.report.tos_issues:
                self.report.tos_issues.append(msg)
        return allowed

    def _load_robots(self, origin: str):
        robots_url = f"{origin}/robots.txt"
        req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            self.report.notes.append(
                f"robots.txt unavailable at {robots_url} ({e}); treating as allowed")
            return None
        # A returned HTML page (block/redirect) is not a valid robots.txt -> allow.
        if "<html" in body[:200].lower() or "Disallow" not in body and "Allow" not in body:
            self.report.notes.append(
                f"{robots_url} has no machine-readable rules; treating as allowed")
            return None
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.splitlines())
        return rp

    # -- requests -------------------------------------------------------------
    def get(self, url: str, *, respect_robots: bool = True, accept: str | None = None,
            ua: str | None = None) -> str | None:
        """GET a URL. Returns body text, or None on a handled failure.

        Records rate-limit / ToS / error signals into self.report.
        """
        if respect_robots and not self._robots_allows(url):
            self.report.status = "partial"
            return None

        self._throttle()
        self.report.http_requests += 1
        headers = {"User-Agent": ua or USER_AGENT}
        if accept:
            headers["Accept"] = accept
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            self._handle_http_error(url, e)
            return None
        except urllib.error.URLError as e:
            self.report.errors.append(f"network error for {url}: {e.reason}")
            self.report.status = "partial"
            return None
        except Exception as e:  # pragma: no cover - defensive
            self.report.errors.append(f"unexpected error for {url}: {e}")
            self.report.status = "partial"
            return None

    def get_json(self, url: str, **kw):
        kw.setdefault("accept", "application/json")
        body = self.get(url, **kw)
        if body is None:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            self.report.errors.append(f"invalid JSON from {url}: {e}")
            self.report.status = "partial"
            return None

    def _handle_http_error(self, url: str, e: urllib.error.HTTPError):
        code = e.code
        if code == 429:
            self.report.rate_limited = True
            retry = e.headers.get("Retry-After")
            note = f"HTTP 429 rate-limited by {url}"
            if retry:
                note += f" (Retry-After: {retry})"
            self.report.tos_issues.append(note)
            self.report.status = "partial"
        elif code == 403:
            # 403 often means a ToS/fair-access block (missing UA, blocked scraper)
            self.report.tos_issues.append(
                f"HTTP 403 forbidden for {url} — likely ToS / access policy block"
            )
            self.report.status = "partial"
        elif code in (401,):
            self.report.tos_issues.append(f"HTTP 401 — auth/API key required for {url}")
            self.report.status = "partial"
        elif code == 404:
            # Several JSON APIs (e.g. openFDA) return 404 to mean "no matching records".
            self.report.notes.append(f"HTTP 404 (no matching records) for {url}")
        else:
            self.report.errors.append(f"HTTP {code} for {url}")
            self.report.status = "partial"
