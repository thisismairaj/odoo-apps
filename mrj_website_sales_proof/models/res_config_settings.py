from odoo import fields, models

P = "mrj_website_sales_proof."


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mrj_sp_enabled = fields.Boolean("Sales popup", config_parameter=P + "enabled", default=True)
    mrj_sp_min_orders = fields.Integer(
        "Minimum real orders", config_parameter=P + "min_orders", default=10,
        help="Order cards stay off until the shop has at least this many confirmed website orders in the period.",
    )
    mrj_sp_days = fields.Integer("Period (days)", config_parameter=P + "days", default=30)
    mrj_sp_show_city = fields.Boolean("Show the buyer's city", config_parameter=P + "show_city", default=True)
    mrj_sp_min_views = fields.Integer(
        "Minimum views today", config_parameter=P + "min_views", default=5,
        help="The 'people viewed this today' card shows only at or above this number of real visitors.",
    )
    mrj_sp_trust = fields.Char(
        "Trust messages", config_parameter=P + "trust",
        help="One message per line, for example 'Free returns within 14 days'. Write only things that are true.",
    )
    mrj_sp_max_cards = fields.Integer("Cards per visit", config_parameter=P + "max_cards", default=3)
