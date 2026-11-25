from odoo import fields, models

from ._mrj_compat import icp_str


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mrj_calendly_token = fields.Char(
        "Calendly personal access token", config_parameter="mrj_calendly_sync.token", groups="base.group_system"
    )
    mrj_calendly_days_back = fields.Integer(
        "Sync bookings from the last (days)", config_parameter="mrj_calendly_sync.days_back", default=30
    )
    mrj_calendly_user_id = fields.Many2one(
        "res.users", "Calendar owner", config_parameter="mrj_calendly_sync.user_id",
        help="The Odoo user whose calendar receives the bookings. Defaults to the administrator.",
    )
    mrj_calendly_last_result = fields.Char("Last sync", compute="_compute_mrj_calendly_last_result")

    def _compute_mrj_calendly_last_result(self):
        value = icp_str(self.env["ir.config_parameter"].sudo(), "mrj_calendly_sync.last_result") or "Never"
        for rec in self:
            rec.mrj_calendly_last_result = value

    def action_mrj_calendly_sync_now(self):
        self.execute()  # save the token first
        result = self.env["calendar.event"]._mrj_calendly_sync()
        kind = "success" if result.split(": ", 1)[-1].startswith("OK") else "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": "Calendly", "message": result, "type": kind, "sticky": kind != "success",
                       "next": {"type": "ir.actions.client", "tag": "reload"}},
        }
