from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    mrj_sp_hidden = fields.Boolean(
        string="Hide from sales popup",
        copy=False,
        help="Never show this order in the shop's sales popup (for example a test order).",
    )
