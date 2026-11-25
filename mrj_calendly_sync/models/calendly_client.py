"""A small read-only client for the Calendly API v2 (personal access token)."""
import logging
import time

import requests

_logger = logging.getLogger(__name__)

API = "https://api.calendly.com"
TIMEOUT = 20


class CalendlyError(Exception):
    """A Calendly error with a message that can be shown to the user."""


class CalendlyClient:
    def __init__(self, token, session=None):
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})

    def _get(self, url, params=None):
        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=TIMEOUT)
            except requests.RequestException as exc:
                raise CalendlyError(f"Could not reach Calendly: {exc}") from exc
            if resp.status_code == 429 and attempt < 2:
                wait = min(int(resp.headers.get("Retry-After", "5") or 5), 30)
                _logger.info("Calendly rate limit, waiting %s s", wait)
                time.sleep(wait)
                continue
            if resp.status_code == 401:
                raise CalendlyError("Calendly refused the token (401). Create a new personal access token and paste it in Settings.")
            if resp.status_code == 403:
                raise CalendlyError("Calendly says this token may not read this data (403).")
            if resp.status_code >= 400:
                raise CalendlyError(f"Calendly returned HTTP {resp.status_code}: {resp.text[:200]}")
            return resp.json()
        raise CalendlyError("Calendly rate limit: try again in a few minutes.")

    def _paged(self, url, params):
        while url:
            data = self._get(url, params)
            yield from data.get("collection", [])
            url = (data.get("pagination") or {}).get("next_page")
            params = None  # next_page already carries the query

    def me(self):
        return self._get(f"{API}/users/me")["resource"]

    def scheduled_events(self, user_uri, min_start_time):
        return self._paged(
            f"{API}/scheduled_events",
            {"user": user_uri, "min_start_time": min_start_time, "count": 100, "sort": "start_time:asc"},
        )

    def invitees(self, event_uri):
        uuid = event_uri.rstrip("/").rsplit("/", 1)[-1]
        return list(self._paged(f"{API}/scheduled_events/{uuid}/invitees", {"count": 100}))
