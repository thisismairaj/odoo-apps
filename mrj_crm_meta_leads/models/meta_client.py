"""A small read-only client for the Meta Graph API (Lead Ads), using a Page access token."""
import json
import logging
import time

import requests

_logger = logging.getLogger(__name__)

TIMEOUT = 20
LEAD_FIELDS = "id,created_time,form_id,field_data,ad_id,ad_name,adset_name,campaign_name,platform,is_organic"
BASIC_FIELDS = "id,created_time,form_id,field_data,ad_id"


class MetaError(Exception):
    """A Meta API error with a message that can be shown to the user."""


class MetaClient:
    def __init__(self, token, version="v27.0", session=None):
        self.token = token
        self.base = f"https://graph.facebook.com/{version or 'v27.0'}"
        self.session = session or requests.Session()
        self._fields = LEAD_FIELDS

    def _get(self, url, params=None):
        params = dict(params or {})
        if "access_token=" not in url:
            params["access_token"] = self.token
        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=TIMEOUT)
            except requests.RequestException as exc:
                raise MetaError(f"Could not reach Meta: {exc.__class__.__name__}") from exc
            try:
                data = resp.json()
            except ValueError:
                data = {}
            err = data.get("error") if isinstance(data, dict) else None
            if resp.status_code < 400 and not err:
                return data
            err = err or {}
            code = err.get("code")
            if code in (4, 17, 32, 613) and attempt < 2:  # rate limits
                time.sleep(10)
                continue
            if code == 190:
                raise MetaError("Meta refused the access token (expired or revoked). Paste a new Page access token in Settings.")
            if code in (10, 200) or (code and 200 <= code < 300):
                raise MetaError(f"Missing permission: {err.get('message', '')[:200]} (the token needs leads_retrieval, "
                                "pages_manage_ads, pages_show_list, pages_read_engagement and ads_management).")
            raise MetaError(f"Meta returned HTTP {resp.status_code}: {err.get('message', resp.text[:200])[:200]}")
        raise MetaError("Meta rate limit: try again in a few minutes.")

    def _paged(self, url, params):
        while url:
            data = self._get(url, params)
            yield from data.get("data", [])
            url = (data.get("paging") or {}).get("next")
            params = None  # the next link already carries the query and token

    def forms(self, page_id):
        return list(self._paged(f"{self.base}/{page_id}/leadgen_forms", {"fields": "id,name,status", "limit": 100}))

    def form_leads(self, form_id, since_unix=0):
        params = {"fields": self._fields, "limit": 100}
        if since_unix:
            params["filtering"] = json.dumps([{"field": "time_created", "operator": "GREATER_THAN", "value": int(since_unix)}])
        try:
            return list(self._paged(f"{self.base}/{form_id}/leads", params))
        except MetaError as exc:
            if "(#100)" not in str(exc):
                raise
            if self._fields == LEAD_FIELDS:
                _logger.info("Meta rejected the extra lead fields, retrying with the basic ones")
                self._fields = BASIC_FIELDS
                return self.form_leads(form_id, since_unix)
            if since_unix:
                # the date filter is documented for ads; if a form refuses it, read all its leads
                # (leads already imported are skipped by their lead ID)
                _logger.info("Meta rejected the date filter on form %s, reading all leads", form_id)
                return self.form_leads(form_id, 0)
            raise

    def lead(self, lead_id):
        try:
            return self._get(f"{self.base}/{lead_id}", {"fields": self._fields})
        except MetaError as exc:
            if self._fields == LEAD_FIELDS and "(#100)" in str(exc):
                self._fields = BASIC_FIELDS
                return self.lead(lead_id)
            raise
