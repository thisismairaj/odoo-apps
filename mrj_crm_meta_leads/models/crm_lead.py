import logging

from markupsafe import Markup

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Meta's standard ("prefill") questions and the crm.lead field each one fills
STANDARD = {
    "full_name": "contact_name",
    "email": "email_from",
    "phone_number": "phone",
    "company_name": "partner_name",
    "job_title": "function",
    "street_address": "street",
    "city": "city",
    "zip_code": "zip",
    "post_code": "zip",
    "website": "website",
}


PLATFORMS = {"fb": "Facebook", "ig": "Instagram"}
UTM_SOURCES = {"Facebook": "utm.utm_source_facebook", "Instagram": "utm.utm_source_instagram"}


def _meta_time(value):
    """Meta sends "2026-11-25T10:00:00+0000" (UTC); Odoo stores naive UTC."""
    try:
        return fields.Datetime.to_datetime(str(value).replace("T", " ")[:19])
    except (TypeError, ValueError):
        return fields.Datetime.now()


def _label(key):
    """Meta's key for a custom question ("when_do_you_want_to_start?") as a readable label with a colon."""
    text = key.replace("_", " ").strip().capitalize()
    return text if text.endswith(("?", ":")) else text + ":"


class CrmLead(models.Model):
    _inherit = "crm.lead"

    mrj_meta_lead_id = fields.Char("Meta lead ID", copy=False, index="btree_not_null", readonly=True)
    mrj_meta_form_id = fields.Many2one("mrj.meta.lead.form", "Meta form", copy=False, readonly=True, index="btree_not_null")
    mrj_meta_campaign = fields.Char("Meta campaign", copy=False, readonly=True)
    mrj_meta_adset = fields.Char("Meta ad set", copy=False, readonly=True)
    mrj_meta_ad = fields.Char("Meta ad", copy=False, readonly=True)
    mrj_meta_platform = fields.Char("Meta platform", copy=False, readonly=True)
    mrj_meta_organic = fields.Boolean("Organic (not from an ad)", copy=False, readonly=True)

    _sql_constraints = [("mrj_meta_lead_id_unique", "UNIQUE(mrj_meta_lead_id)", "This Meta lead is already in CRM.")]

    @api.model
    def _mrj_meta_vals(self, data, form):
        answers = {}
        for item in data.get("field_data") or []:
            values = [str(v) for v in item.get("values") or [] if v not in (None, "")]
            if item.get("name") and values:
                answers[item["name"]] = ", ".join(values)
        vals = {}
        for key, field in STANDARD.items():
            if answers.get(key) and field not in vals:
                vals[field] = answers[key]
        if not vals.get("contact_name"):
            first, last = answers.get("first_name", ""), answers.get("last_name", "")
            if first or last:
                vals["contact_name"] = f"{first} {last}".strip()
        country = answers.get("country")
        if country:
            Country = self.env["res.country"].sudo()
            match = Country.search([("code", "=ilike", country)], limit=1) if len(country) == 2 else Country
            match = match or Country.search([("name", "=ilike", country)], limit=1)
            if match:
                vals["country_id"] = match.id
                state = answers.get("state") or answers.get("province")
                if state:
                    st = self.env["res.country.state"].sudo().search(
                        [("country_id", "=", match.id), "|", ("code", "=ilike", state), ("name", "=ilike", state)], limit=1)
                    vals["state_id"] = st.id or False
        used = set(STANDARD) | {"first_name", "last_name", "country", "state", "province"}
        rows = Markup().join(
            Markup("<li><b>%s</b> %s</li>") % (_label(k), v) for k, v in answers.items() if k not in used)
        platform = PLATFORMS.get(data.get("platform") or "", data.get("platform") or "")
        source_name = "Instagram" if platform == "Instagram" else "Facebook"
        utm_source = self.env.ref(UTM_SOURCES[source_name], raise_if_not_found=False)
        if not utm_source:  # older versions ship no Instagram source
            Source = self.env["utm.source"].sudo()
            utm_source = Source.search([("name", "=", source_name)], limit=1) or Source.create({"name": source_name})
        utm_medium = self.env.ref("utm.utm_medium_social_media", raise_if_not_found=False)
        campaign = False
        if data.get("campaign_name"):
            Campaign = self.env["utm.campaign"].sudo()
            campaign = Campaign.search([("title", "=", data["campaign_name"])], limit=1) or Campaign.create(
                {"title": data["campaign_name"]})
        source = data.get("campaign_name") or data.get("ad_name") or ("organic" if data.get("is_organic") else "")
        intro = Markup("<p>Lead from the Meta form <b>%s</b>%s.</p>") % (
            form.name, Markup(", %s") % source if source else "")
        who = vals.get("contact_name") or vals.get("email_from") or vals.get("phone") or data.get("id")
        vals.update({
            "name": f"{form.name}: {who}",
            "type": form.lead_type,
            "description": intro + (Markup("<ul>%s</ul>") % rows if rows else Markup()),
            "team_id": form.team_id.id or False,
            "user_id": form.user_id.id or False,
            "tag_ids": [(6, 0, form.tag_ids.ids)],
            "mrj_meta_lead_id": str(data["id"]),
            "mrj_meta_form_id": form.id,
            "mrj_meta_campaign": data.get("campaign_name") or False,
            "mrj_meta_adset": data.get("adset_name") or False,
            "mrj_meta_ad": data.get("ad_name") or False,
            "mrj_meta_platform": platform or False,
            "campaign_id": campaign.id if campaign else False,
            "source_id": utm_source.id if utm_source else False,
            "medium_id": utm_medium.id if utm_medium else False,
            "mrj_meta_organic": bool(data.get("is_organic")),
        })
        return vals

    @api.model
    def _mrj_meta_import(self, data, form):
        """Create one CRM lead from a Meta lead. Returns the new lead, or False if it was already imported."""
        if not data.get("id"):
            return False
        Lead = self.sudo().with_context(active_test=False, mail_create_nosubscribe=True)
        if Lead.search_count([("mrj_meta_lead_id", "=", str(data["id"]))], limit=1):
            return False
        vals = self._mrj_meta_vals(data, form)
        if not form.team_id:
            vals.pop("team_id")  # let Odoo pick the salesperson's team
        lead = Lead.create(vals)
        created = _meta_time(data.get("created_time"))
        if not form.last_lead_time or created > form.last_lead_time:
            form.sudo().last_lead_time = created
        return lead
