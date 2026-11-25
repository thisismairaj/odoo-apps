import logging
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import api, fields, models

from ._mrj_compat import icp_int, icp_str

from .calendly_client import CalendlyClient, CalendlyError

_logger = logging.getLogger(__name__)

PARAM = "mrj_calendly_sync."
# Calendly already emails invitees, so Odoo must not send invitations or updates for synced bookings.
QUIET = {"no_mail_to_attendees": True, "skip_attendee_notification": True, "mail_create_nolog": True, "mail_notrack": True}


def _to_odoo_dt(value):
    """Calendly sends ISO 8601 UTC ("2026-11-25T10:00:00.000000Z"); Odoo stores naive UTC."""
    return fields.Datetime.to_datetime(value.replace("T", " ")[:19])


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    mrj_calendly_uri = fields.Char("Calendly event", copy=False, index="btree_not_null", readonly=True)

    _sql_constraints = [
        ("mrj_calendly_uri_unique", "UNIQUE(mrj_calendly_uri)", "This Calendly booking is already in the calendar."),
    ]

    @api.model
    def _mrj_calendly_cron(self):
        self._mrj_calendly_sync()

    @api.model
    def _mrj_calendly_sync(self, client=None):
        """Fetch Calendly bookings and create or update calendar events. Returns a short result text."""
        icp = self.env["ir.config_parameter"].sudo()
        token = icp_str(icp, PARAM + "token")
        if not token and client is None:
            return self._mrj_calendly_result("Not synced: no Calendly token in Settings.")
        days = icp_int(icp, PARAM + "days_back", 30) or 30
        owner = self.env["res.users"].sudo().browse(icp_int(icp, PARAM + "user_id")).exists() or self.env.ref("base.user_admin")
        client = client or CalendlyClient(token)
        created = updated = moved = archived = 0
        try:
            me = client.me()
            since = (fields.Datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
            Event = self.sudo().with_context(active_test=False, **QUIET)
            events = list(client.scheduled_events(me["uri"], since))
            invitees_of = {ev["uri"]: client.invitees(ev["uri"]) for ev in events}
            # Calendly reschedules by cancelling the booking and creating a new one. The cancelled
            # invitee points to its replacement, so the same Odoo event can be moved instead.
            replaced_by = {}
            for ev in events:
                if ev.get("status") == "canceled":
                    for inv in invitees_of[ev["uri"]]:
                        if inv.get("rescheduled") and inv.get("new_invitee"):
                            replaced_by[ev["uri"]] = inv["new_invitee"].split("/invitees/")[0]
            replaces = {new: old for old, new in replaced_by.items()}
            active_uris = {ev["uri"] for ev in events if ev.get("status") != "canceled"}

            for ev in events:
                existing = Event.search([("mrj_calendly_uri", "=", ev["uri"])], limit=1)
                if ev.get("status") == "canceled":
                    if replaced_by.get(ev["uri"]) in active_uris:
                        continue  # moved to its replacement below
                    if existing and existing.active:
                        existing.write({"active": False})
                        archived += 1
                    continue
                invitees = [i for i in invitees_of[ev["uri"]] if i.get("status") != "canceled"]
                vals = self._mrj_calendly_vals(ev, invitees, owner)
                update_vals = {k: v for k, v in vals.items() if k != "description"}  # keep notes users added in Odoo
                if not existing and ev["uri"] in replaces:
                    existing = Event.search([("mrj_calendly_uri", "=", replaces[ev["uri"]])], limit=1)
                    if existing:
                        existing.write(update_vals)  # takes the new Calendly id, time and link
                        moved += 1
                        continue
                if existing:
                    existing.write(update_vals)
                    updated += 1
                else:
                    Event.create(vals)
                    created += 1
        except CalendlyError as exc:
            return self._mrj_calendly_result(f"Failed: {exc}")
        return self._mrj_calendly_result(
            f"OK: {created} new, {updated} updated, {moved} rescheduled, {archived} cancelled."
        )

    def _mrj_calendly_result(self, text):
        stamp = fields.Datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        result = f"{stamp}: {text}"
        self.env["ir.config_parameter"].sudo().set_param(PARAM + "last_result", result)
        _logger.info("Calendly sync %s", result)
        return result

    @api.model
    def _mrj_calendly_vals(self, ev, invitees, owner):
        partners = owner.partner_id
        for inv in invitees:
            email = (inv.get("email") or "").strip().lower()
            if not email:
                continue
            partner = self.env["res.partner"].sudo().search([("email", "=ilike", email)], limit=1)
            partners |= partner or self.env["res.partner"].sudo().create({"name": inv.get("name") or email, "email": email})
        location = ev.get("location") or {}
        join_url = location.get("join_url") or ""
        place = location.get("location") or ""  # address or phone for in-person and phone meetings
        names = ", ".join(i.get("name") or i.get("email") or "" for i in invitees)
        parts = []
        for inv in invitees:
            qa = Markup().join(
                Markup("<li><b>%s</b> %s</li>") % (q.get("question", ""), q.get("answer", ""))
                for q in inv.get("questions_and_answers") or []
            )
            parts.append(Markup("<p>%s (%s)</p>") % (inv.get("name", ""), inv.get("email", "")) + (Markup("<ul>%s</ul>") % qa if qa else Markup()))
        notes = Markup("<p>Booked through Calendly.</p>") + Markup().join(parts)
        return {
            "name": f"{ev.get('name') or 'Calendly booking'}: {names}" if names else (ev.get("name") or "Calendly booking"),
            "start": _to_odoo_dt(ev["start_time"]),
            "stop": _to_odoo_dt(ev["end_time"]),
            "location": place,
            "videocall_location": join_url or False,
            "description": notes,
            "user_id": owner.id,
            "partner_ids": [(6, 0, partners.ids)],
            "mrj_calendly_uri": ev["uri"],
            "active": True,
        }
