from odoo import fields, models

P = "mrj_crm_meta_leads."


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mrj_meta_page_id = fields.Char("Facebook Page ID", config_parameter=P + "page_id", groups="base.group_system")
    mrj_meta_token = fields.Char("Page access token", config_parameter=P + "token", groups="base.group_system")
    mrj_meta_app_secret = fields.Char("App secret (webhook)", config_parameter=P + "app_secret", groups="base.group_system")
    mrj_meta_verify_token = fields.Char("Webhook verify token", config_parameter=P + "verify_token", groups="base.group_system")
    mrj_meta_version = fields.Char("Graph API version", config_parameter=P + "version", default="v27.0")
    mrj_meta_days_back = fields.Integer("First sync: leads from the last (days)", config_parameter=P + "days_back", default=30)
    mrj_meta_webhook_url = fields.Char("Webhook URL", compute="_compute_mrj_meta_info")
    mrj_meta_last_result = fields.Char("Last Meta import", compute="_compute_mrj_meta_info")

    def _compute_mrj_meta_info(self):
        icp = self.env["ir.config_parameter"].sudo()
        base = icp.get_str("web.base.url") or ""
        last = icp.get_str(P + "last_result") or "Never"
        for rec in self:
            rec.mrj_meta_webhook_url = f"{base}/mrj_meta_leads/webhook"
            rec.mrj_meta_last_result = last

    def _mrj_meta_notify(self, message, ok):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": "Meta Lead Ads", "message": message, "type": "success" if ok else "warning",
                       "sticky": not ok, "next": {"type": "ir.actions.client", "tag": "reload"}},
        }

    def action_mrj_meta_load_forms(self):
        self.execute()  # save the settings first
        ok, msg = self.env["mrj.meta.lead.form"]._mrj_load_forms()
        return self._mrj_meta_notify(msg, ok)

    def action_mrj_meta_sync_now(self):
        self.execute()
        result = self.env["mrj.meta.lead.form"]._mrj_sync()
        return self._mrj_meta_notify(result, result.split(": ", 1)[-1].startswith("OK"))
