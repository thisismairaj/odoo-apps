import re

from odoo import http
from odoo.http import request

BOTS = re.compile(r"bot|crawl|spider|slurp|headless|preview|fetch|monitor|lighthouse", re.I)


class SalesProofController(http.Controller):
    @http.route("/mrj_sales_proof/cards", type="jsonrpc", auth="public", website=True, methods=["POST"])
    def cards(self, product_template_id=None, **kw):
        website = request.env.website
        template = None
        if product_template_id:
            template = request.env["product.template"].sudo().browse(int(product_template_id)).exists()
            if template and not template.is_published:
                template = None
        if template and self._mrj_countable():
            hr = request.httprequest
            request.env["mrj.sales.proof.view"]._mrj_add_view(template, hr.remote_addr, hr.headers.get("User-Agent"))
        return website._mrj_sp_cards(template)

    @staticmethod
    def _mrj_countable():
        """Count real shoppers only: no logged-in staff, no bots, no prefetch."""
        hr = request.httprequest
        if not request.env.user._is_public() and request.env.user._is_internal():
            return False
        if BOTS.search(hr.headers.get("User-Agent") or ""):
            return False
        purpose = (hr.headers.get("Purpose") or hr.headers.get("Sec-Purpose") or "").lower()
        return "prefetch" not in purpose
