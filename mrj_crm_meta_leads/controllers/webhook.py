import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

from ..models.meta_client import MetaError

_logger = logging.getLogger(__name__)


def signature_ok(body, header, secret):
    """Meta signs the raw body: X-Hub-Signature-256: sha256=<HMAC-SHA256 hex with the app secret>."""
    if not (secret and header and header.startswith("sha256=")):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[7:])


class MetaLeadsWebhook(http.Controller):
    @http.route("/mrj_meta_leads/webhook", type="http", auth="public", methods=["GET", "POST"], csrf=False, save_session=False)
    def webhook(self, **params):
        Form = request.env["mrj.meta.lead.form"].sudo()
        settings = Form._mrj_settings()
        if request.httprequest.method == "GET":  # Meta checks the URL when the webhook is added
            token = params.get("hub.verify_token") or ""
            if params.get("hub.mode") == "subscribe" and settings["verify_token"] and hmac.compare_digest(
                    token, settings["verify_token"]):
                return request.make_response(params.get("hub.challenge", ""), [("Content-Type", "text/plain")])
            return request.make_response("forbidden", status=403)

        body = request.httprequest.get_data()
        if not signature_ok(body, request.httprequest.headers.get("X-Hub-Signature-256", ""), settings["app_secret"]):
            _logger.warning("Meta Lead Ads webhook: bad or missing signature, ignored")
            return request.make_response("bad signature", status=403)
        try:
            payload = json.loads(body or b"{}")
        except ValueError:
            return request.make_response("bad json", status=400)
        client = Form._mrj_client()
        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                if change.get("field") != "leadgen" or not value.get("leadgen_id"):
                    continue
                form = Form.with_context(active_test=False).search([("form_id", "=", str(value.get("form_id")))], limit=1)
                if not form:
                    form = Form.create({"name": f"Form {value.get('form_id')}", "form_id": str(value.get("form_id")),
                                        "page_id": str(value.get("page_id") or "")})
                if not form.active or not client:
                    continue
                try:
                    data = client.lead(value["leadgen_id"])
                except MetaError as exc:
                    _logger.warning("Meta Lead Ads webhook: could not read lead %s: %s", value["leadgen_id"], exc)
                    continue  # the scheduled sync will pick it up
                request.env["crm.lead"].sudo()._mrj_meta_import(data, form)
        return request.make_response("ok")
