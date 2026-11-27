import logging
from datetime import timedelta, timezone

from odoo import api, fields, models

from .meta_client import MetaClient, MetaError

_logger = logging.getLogger(__name__)
P = "mrj_crm_meta_leads."


def _unix(dt):
    """Naive UTC datetime to a unix timestamp."""
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


class MetaLeadForm(models.Model):
    _name = "mrj.meta.lead.form"
    _description = "Meta Lead Ads form"
    _order = "name"

    name = fields.Char(required=True)
    form_id = fields.Char("Meta form ID", required=True, copy=False)
    page_id = fields.Char("Page ID")
    status = fields.Char("Status on Meta", readonly=True)
    active = fields.Boolean(default=True, help="Untick to stop importing this form's leads.")
    team_id = fields.Many2one("crm.team", "Sales team")
    user_id = fields.Many2one("res.users", "Salesperson", domain=[("share", "=", False)])
    tag_ids = fields.Many2many("crm.tag", string="Tags")
    lead_type = fields.Selection(
        [("lead", "Lead"), ("opportunity", "Opportunity")], default="lead", required=True,
        help="Use Opportunity when the Leads step is turned off in CRM settings.")
    last_lead_time = fields.Datetime("Newest lead imported", readonly=True, copy=False)
    lead_count = fields.Integer(compute="_compute_lead_count")

    _form_id_unique = models.Constraint("UNIQUE(form_id)", "This Meta form is already listed.")

    def _compute_lead_count(self):
        data = self.env["crm.lead"].with_context(active_test=False)._read_group(
            [("mrj_meta_form_id", "in", self.ids)], ["mrj_meta_form_id"], ["__count"])
        counts = {form.id: n for form, n in data}
        for rec in self:
            rec.lead_count = counts.get(rec.id, 0)

    def action_view_leads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": self.name, "res_model": "crm.lead",
            "view_mode": "list,form", "domain": [("mrj_meta_form_id", "=", self.id)],
            "context": {"active_test": False},
        }

    # ---- settings and client ------------------------------------------------------------
    @api.model
    def _mrj_settings(self):
        icp = self.env["ir.config_parameter"].sudo()
        s = {k: icp.get_str(P + k) or "" for k in ("page_id", "token", "app_secret", "verify_token", "version")}
        s["days_back"] = icp.get_int(P + "days_back", 30) or 30
        return s

    @api.model
    def _mrj_client(self):
        s = self._mrj_settings()
        return MetaClient(s["token"], s["version"] or "v27.0") if s["token"] else None

    @api.model
    def _mrj_result(self, text):
        result = f"{fields.Datetime.now().strftime('%Y-%m-%d %H:%M UTC')}: {text}"
        self.env["ir.config_parameter"].sudo().set_str(P + "last_result", result)
        _logger.info("Meta Lead Ads %s", result)
        return result

    # ---- forms ---------------------------------------------------------------------------
    @api.model
    def _mrj_load_forms(self, client=None):
        s = self._mrj_settings()
        client = client or self._mrj_client()
        if not client or not s["page_id"]:
            return False, "Fill in the Page ID and the Page access token first."
        try:
            forms = client.forms(s["page_id"])
        except MetaError as exc:
            return False, str(exc)
        Form = self.sudo().with_context(active_test=False)
        new = 0
        for f in forms:
            rec = Form.search([("form_id", "=", f["id"])], limit=1)
            vals = {"name": f.get("name") or f["id"], "status": f.get("status") or "", "page_id": s["page_id"]}
            if rec:
                rec.write(vals)
            else:
                Form.create(dict(vals, form_id=f["id"], active=(f.get("status") or "ACTIVE") == "ACTIVE"))
                new += 1
        return True, f"{len(forms)} forms on the Page, {new} new."

    # ---- sync ----------------------------------------------------------------------------
    @api.model
    def _mrj_cron(self):
        self._mrj_sync()

    @api.model
    def _mrj_sync(self, client=None):
        client = client or self._mrj_client()
        if not client:
            return self._mrj_result("Not synced: no Page access token in Settings.")
        days = self._mrj_settings()["days_back"]
        created = skipped = 0
        errors = []
        for form in self.sudo().search([]):
            since = form.last_lead_time or (fields.Datetime.now() - timedelta(days=days))
            try:
                # a minute of overlap; leads already imported are skipped by their Meta lead ID
                leads = client.form_leads(form.form_id, _unix(since) - 60)
            except MetaError as exc:
                errors.append(f"{form.name}: {exc}")
                continue
            for data in leads:
                if self.env["crm.lead"]._mrj_meta_import(data, form):
                    created += 1
                else:
                    skipped += 1
        if errors:
            return self._mrj_result(f"Partly failed: {created} new leads. " + " | ".join(errors)[:400])
        return self._mrj_result(f"OK: {created} new leads, {skipped} already in CRM.")
