import hashlib
from datetime import timedelta

from odoo import _, api, fields, models

from ._mrj_compat import icp_bool, icp_int, icp_str

P = "mrj_website_sales_proof."


class SalesProofView(models.Model):
    """One row per visitor, product and day. Only a salted hash is kept, never the IP address."""

    _name = "mrj.sales.proof.view"
    _description = "Sales popup: product view today"

    product_tmpl_id = fields.Many2one("product.template", required=True, ondelete="cascade", index=True)
    day = fields.Date(required=True, index=True)
    visitor_hash = fields.Char(required=True)

    _mrj_unique_view = models.Constraint(
        "UNIQUE(product_tmpl_id, day, visitor_hash)", "A visitor is counted once per product and day."
    )

    @api.model
    def _mrj_visitor_hash(self, ip, user_agent, day):
        secret = icp_str(self.env["ir.config_parameter"].sudo(), "database.secret")
        raw = "|".join([secret, ip or "", user_agent or "", str(day)])
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    @api.model
    def _mrj_add_view(self, template, ip, user_agent):
        day = fields.Date.context_today(self)
        vals = {"product_tmpl_id": template.id, "day": day,
                "visitor_hash": self._mrj_visitor_hash(ip, user_agent, day)}
        exists = self.sudo().search_count([(k, "=", v) for k, v in vals.items()], limit=1)
        if not exists:
            self.sudo().create(vals)

    @api.model
    def _mrj_views_today(self, template):
        day = fields.Date.context_today(self)
        return self.sudo().search_count([("product_tmpl_id", "=", template.id), ("day", "=", day)])

    @api.model
    def _mrj_cleanup(self):
        self.sudo().search([("day", "<", fields.Date.today() - timedelta(days=2))]).unlink()


class Website(models.Model):
    _inherit = "website"

    def _mrj_sp_settings(self):
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "enabled": icp_bool(icp, P + "enabled", True),
            "min_orders": max(1, icp_int(icp, P + "min_orders", 10)),
            "days": max(1, icp_int(icp, P + "days", 30)),
            "show_city": icp_bool(icp, P + "show_city", True),
            "min_views": max(1, icp_int(icp, P + "min_views", 5)),
            "trust": [t.strip() for t in (icp_str(icp, P + "trust") or "").splitlines() if t.strip()],
            "max_cards": max(1, icp_int(icp, P + "max_cards", 3)),
        }

    @staticmethod
    def _mrj_order_product(order):
        for line in order.order_line:
            if line.display_type or line.is_downpayment or not line.product_id:
                continue
            if getattr(line, "is_delivery", False):
                continue
            tmpl = line.product_id.product_tmpl_id
            if tmpl.is_published and tmpl.sale_ok:
                return tmpl
        return None

    def _mrj_sp_order_cards(self, cfg=None):
        """Cards for real confirmed orders of this website, or [] while there are fewer than the minimum."""
        self.ensure_one()
        cfg = cfg or self._mrj_sp_settings()
        orders_model = self.env["sale.order"].sudo()
        domain = [
            ("website_id", "=", self.id),
            ("state", "=", "sale"),
            ("mrj_sp_hidden", "=", False),
            ("date_order", ">=", fields.Datetime.now() - timedelta(days=cfg["days"])),
        ]
        if orders_model.search_count(domain) < cfg["min_orders"]:
            return []
        cards = []
        for order in orders_model.search(domain, order="date_order desc", limit=20):
            tmpl = self._mrj_order_product(order)
            if not tmpl:
                continue
            partner = order.partner_id
            if partner.is_company:
                first = _("A customer")  # company names are not first names
            else:
                first = (partner.name or "").strip().split(" ")[0].capitalize() or _("Someone")
            city = (order.partner_shipping_id.city or partner.city or "").strip().title()
            who = _("%(name)s from %(city)s", name=first, city=city) if cfg["show_city"] and city else first
            cards.append({
                "kind": "order",
                "text": _("%(who)s ordered", who=who),
                "product": tmpl.with_context(lang=self.env.lang).name,
                "url": tmpl.website_url,
                "img": "/web/image/product.template/%s/image_128" % tmpl.id,
                "at": order.date_order.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
        return cards

    def _mrj_sp_cards(self, template=None):
        """Everything the popup may show on this page, in order: orders, views today, trust messages."""
        self.ensure_one()
        cfg = self._mrj_sp_settings()
        if not cfg["enabled"]:
            return {"cards": [], "max": 0}
        cards = self._mrj_sp_order_cards(cfg)
        if template:
            views = self.env["mrj.sales.proof.view"]._mrj_views_today(template)
            if views >= cfg["min_views"]:
                cards.insert(0, {"kind": "views", "text": _("%(n)s people viewed this product today", n=views)})
        cards += [{"kind": "trust", "text": t} for t in cfg["trust"]]
        return {"cards": cards, "max": cfg["max_cards"]}
