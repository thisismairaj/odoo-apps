from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged

from ..models.calendly_client import CalendlyError

ME = {"uri": "https://api.calendly.com/users/ME", "name": "Owner"}


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000000Z")


class FakeCalendly:
    """Stands in for CalendlyClient with fixed bookings."""

    def __init__(self, events, invitees):
        self.events, self.inv = events, invitees

    def me(self):
        return ME

    def scheduled_events(self, user_uri, min_start_time):
        assert user_uri == ME["uri"]
        return iter(self.events)

    def invitees(self, event_uri):
        return self.inv.get(event_uri, [])


@tagged("post_install", "-at_install")
class TestCalendlySync(TransactionCase):
    def setUp(self):
        super().setUp()
        start = fields.Datetime.now().replace(microsecond=0) + timedelta(days=2)
        self.ev_uri = "https://api.calendly.com/scheduled_events/AAA"
        self.event = {
            "uri": self.ev_uri, "name": "30 Minute Meeting", "status": "active",
            "start_time": iso(start), "end_time": iso(start + timedelta(minutes=30)),
            "location": {"type": "google_conference", "join_url": "https://meet.example.com/abc"},
        }
        self.invitees = {self.ev_uri: [{
            "name": "Sara Khan", "email": "Sara@Example.com", "status": "active",
            "questions_and_answers": [{"question": "What do you need?", "answer": "A demo <b>please</b>"}],
        }]}
        self.start = start
        self.Event = self.env["calendar.event"].with_context(active_test=False)

    def test_create_update_cancel(self):
        result = self.env["calendar.event"]._mrj_calendly_sync(client=FakeCalendly([self.event], self.invitees))
        self.assertIn("OK: 1 new, 0 updated, 0 rescheduled, 0 cancelled", result)
        ev = self.Event.search([("mrj_calendly_uri", "=", self.ev_uri)])
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev.name, "30 Minute Meeting: Sara Khan")
        self.assertEqual(ev.start, self.start)
        self.assertEqual(ev.videocall_location, "https://meet.example.com/abc")
        self.assertIn("sara@example.com", ev.partner_ids.mapped("email"))
        self.assertIn("&lt;b&gt;please&lt;/b&gt;", str(ev.description), "answers must be escaped")
        self.assertIn("<li><b>What do you need?</b>", str(ev.description))

        # Running again updates, never duplicates.
        moved = dict(self.event, start_time=iso(self.start + timedelta(hours=1)), end_time=iso(self.start + timedelta(hours=2)))
        result = self.env["calendar.event"]._mrj_calendly_sync(client=FakeCalendly([moved], self.invitees))
        self.assertIn("0 new, 1 updated", result)
        self.assertEqual(self.Event.search_count([("mrj_calendly_uri", "=", self.ev_uri)]), 1)
        self.assertEqual(ev.start, self.start + timedelta(hours=1))

        # Same email again: reuse the contact, don't create a second one.
        self.assertEqual(self.env["res.partner"].search_count([("email", "=ilike", "sara@example.com")]), 1)

        # Cancelled in Calendly: archived in Odoo.
        cancelled = dict(moved, status="canceled")
        result = self.env["calendar.event"]._mrj_calendly_sync(client=FakeCalendly([cancelled], self.invitees))
        self.assertIn("1 cancelled", result)
        self.assertFalse(ev.active)

    def test_reschedule_moves_the_same_event(self):
        """Calendly reschedules by cancelling the booking and creating a new one (seen on a real account)."""
        self.env["calendar.event"]._mrj_calendly_sync(client=FakeCalendly([self.event], self.invitees))
        ev = self.Event.search([("mrj_calendly_uri", "=", self.ev_uri)])
        ev.description = "<p>Bring the contract.</p>"  # something a user added in Odoo
        new_uri = "https://api.calendly.com/scheduled_events/BBB"
        old = dict(self.event, status="canceled")
        new = dict(self.event, uri=new_uri, start_time=iso(self.start + timedelta(days=1)),
                   end_time=iso(self.start + timedelta(days=1, minutes=30)))
        old_inv = [dict(self.invitees[self.ev_uri][0], status="canceled", rescheduled=True,
                        new_invitee=new_uri + "/invitees/X1")]
        fake = FakeCalendly([new, old], {self.ev_uri: old_inv, new_uri: self.invitees[self.ev_uri]})
        result = self.env["calendar.event"]._mrj_calendly_sync(client=fake)
        self.assertIn("0 new, 0 updated, 1 rescheduled, 0 cancelled", result)
        self.assertTrue(ev.active)
        self.assertEqual(ev.mrj_calendly_uri, new_uri)
        self.assertEqual(ev.start, self.start + timedelta(days=1))
        self.assertIn("Bring the contract.", str(ev.description), "notes added in Odoo must survive")
        self.assertEqual(self.Event.search_count([("name", "=", ev.name)]), 1, "no second event")
        # A later sync sees the new booking as an ordinary update.
        self.assertIn("0 new, 1 updated, 0 rescheduled, 0 cancelled",
                      self.env["calendar.event"]._mrj_calendly_sync(client=fake))

    def test_no_invitation_emails(self):
        before = self.env["mail.mail"].search_count([])
        self.env["calendar.event"]._mrj_calendly_sync(client=FakeCalendly([self.event], self.invitees))
        self.assertEqual(self.env["mail.mail"].search_count([]), before, "no email of any kind may be queued")
        mails = self.env["mail.mail"].search([("email_to", "ilike", "sara@example.com")])
        self.assertFalse(mails, "Calendly already emails invitees; Odoo must not")

    def test_no_token(self):
        self.env["ir.config_parameter"].sudo().set_param("mrj_calendly_sync.token", False)
        self.assertIn("no Calendly token", self.env["calendar.event"]._mrj_calendly_sync())

    def test_error_is_reported(self):
        class Broken(FakeCalendly):
            def me(self):
                raise CalendlyError("Calendly refused the token (401).")
        result = self.env["calendar.event"]._mrj_calendly_sync(client=Broken([], {}))
        self.assertIn("Failed: Calendly refused the token", result)
        self.assertIn("Failed", self.env["ir.config_parameter"].sudo().get_param("mrj_calendly_sync.last_result"))
