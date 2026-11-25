from odoo.tests import HttpCase, TransactionCase, tagged

P = "mrj_website_sales_proof."


@tagged("post_install", "-at_install")
class TestSalesProof(TransactionCase):
    def setUp(self):
        super().setUp()
        self.website = self.env["website"].create({"name": "Popup test shop"})
        self.icp = self.env["ir.config_parameter"].sudo()
        self.icp.set_param(P + "min_orders", "3")
        self.icp.set_param(P + "min_views", "2")
        self.icp.set_param(P + "trust", "Free returns within 14 days\n\n  Cash on delivery  ")
        self.tmpl = self.env["product.template"].create({
            "name": "Linen Shirt", "list_price": 30, "is_published": True, "sale_ok": True, "type": "consu",
        })
        self.buyer = self.env["res.partner"].create({"name": "ayesha khan", "city": "lahore"})

    def _order(self, hidden=False, confirm=True):
        order = self.env["sale.order"].create({
            "partner_id": self.buyer.id, "website_id": self.website.id, "mrj_sp_hidden": hidden,
            "order_line": [(0, 0, {"product_id": self.tmpl.product_variant_id.id, "product_uom_qty": 1})],
        })
        if confirm:
            order.action_confirm()
        return order

    def _kinds(self, data):
        return [c["kind"] for c in data["cards"]]

    def test_orders_hidden_below_minimum(self):
        self._order()
        self._order()
        self._order(confirm=False)  # quotations never count
        self._order(hidden=True)    # hidden orders never count
        self.assertEqual(self.website._mrj_sp_order_cards(), [])

    def test_orders_shown_at_minimum_first_name_only(self):
        for _i in range(3):
            self._order()
        self._order(hidden=True)
        cards = self.website._mrj_sp_order_cards()
        self.assertEqual(len(cards), 3)
        self.assertEqual(cards[0]["text"], "Ayesha from Lahore ordered")
        self.assertEqual(cards[0]["product"], "Linen Shirt")
        self.assertNotIn("Khan", str(cards))

    def test_city_can_be_turned_off(self):
        for _i in range(3):
            self._order()
        self.icp.set_param(P + "show_city", "0")
        self.assertEqual(self.website._mrj_sp_order_cards()[0]["text"], "Ayesha ordered")

    def test_company_buyer_is_not_named(self):
        self.buyer.write({"name": "Gulf Trading LLC", "is_company": True})
        for _i in range(3):
            self._order()
        self.assertEqual(self.website._mrj_sp_order_cards()[0]["text"], "A customer from Lahore ordered")

    def test_unpublished_product_not_shown(self):
        for _i in range(3):
            self._order()
        self.tmpl.is_published = False
        self.assertEqual(self.website._mrj_sp_order_cards(), [])

    def test_views_counted_once_per_visitor(self):
        views = self.env["mrj.sales.proof.view"]
        views._mrj_add_view(self.tmpl, "1.1.1.1", "Firefox")
        views._mrj_add_view(self.tmpl, "1.1.1.1", "Firefox")
        self.assertEqual(views._mrj_views_today(self.tmpl), 1)
        self.assertNotIn("views", self._kinds(self.website._mrj_sp_cards(self.tmpl)))
        views._mrj_add_view(self.tmpl, "2.2.2.2", "Firefox")
        data = self.website._mrj_sp_cards(self.tmpl)
        self.assertEqual(data["cards"][0]["text"], "2 people viewed this product today")
        hashes = views.sudo().search([("product_tmpl_id", "=", self.tmpl.id)]).mapped("visitor_hash")
        self.assertFalse([h for h in hashes if "1.1.1.1" in h])

    def test_trust_lines_and_switch_off(self):
        data = self.website._mrj_sp_cards()
        self.assertEqual([c["text"] for c in data["cards"]], ["Free returns within 14 days", "Cash on delivery"])
        self.assertEqual(data["max"], 3)
        self.icp.set_param(P + "enabled", "0")
        self.assertEqual(self.website._mrj_sp_cards(), {"cards": [], "max": 0})


@tagged("post_install", "-at_install")
class TestSalesProofRoute(HttpCase):
    def test_route_counts_shoppers_not_bots(self):
        tmpl = self.env["product.template"].create({"name": "Route Shirt", "is_published": True})
        url = "/mrj_sales_proof/cards"
        res = self.make_jsonrpc_request(url, {"product_template_id": tmpl.id})
        self.assertIn("cards", res)
        self.assertEqual(self.env["mrj.sales.proof.view"]._mrj_views_today(tmpl), 1)
        self.make_jsonrpc_request(url, {"product_template_id": tmpl.id}, headers={"User-Agent": "Googlebot/2.1"})
        self.assertEqual(self.env["mrj.sales.proof.view"]._mrj_views_today(tmpl), 1)


@tagged("post_install", "-at_install")
class TestSalesProofSettings(TransactionCase):
    def test_unticked_boxes_stay_unticked(self):
        """Odoo deletes a False config parameter, so a box on by default must be stored as "0"."""
        self.env["res.config.settings"].create({"mrj_sp_enabled": False, "mrj_sp_show_city": False}).execute()
        fresh = self.env["res.config.settings"].create({})
        self.assertFalse(fresh.mrj_sp_enabled)
        self.assertFalse(fresh.mrj_sp_show_city)
        self.assertEqual(self.env["website"].search([], limit=1)._mrj_sp_cards(), {"cards": [], "max": 0})
        self.env["res.config.settings"].create({"mrj_sp_enabled": True}).execute()
        self.assertTrue(self.env["res.config.settings"].create({}).mrj_sp_enabled)
