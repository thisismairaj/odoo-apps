import hashlib
import hmac
import json

from odoo.tests import HttpCase, TransactionCase, tagged

from ..controllers.webhook import signature_ok
from ..models.meta_client import MetaError

P = "mrj_crm_meta_leads."


def lead(lead_id, form_id="F1", **extra):
    data = {
        "id": lead_id, "form_id": form_id, "created_time": "2026-11-25T10:00:00+0000",
        "field_data": [
            {"name": "full_name", "values": ["Sara Khan"]},
            {"name": "email", "values": ["sara@example.com"]},
            {"name": "phone_number", "values": ["+966500000000"]},
            {"name": "country", "values": ["SA"]},
            {"name": "what_do_you_need?", "values": ["A demo <b>please</b>"]},
        ],
        "campaign_name": "Winter sale", "adset_name": "Riyadh", "ad_name": "Video 1", "platform": "ig",
    }
    data.update(extra)
    return data


class FakeMeta:
    def __init__(self, leads=None, forms=None, fail=False):
        self.leads, self.forms_list, self.fail, self.calls = leads or {}, forms or [], fail, []

    def forms(self, page_id):
        return self.forms_list

    def form_leads(self, form_id, since_unix=0):
        self.calls.append((form_id, since_unix))
        if self.fail:
            raise MetaError("Meta refused the access token (expired or revoked).")
        return self.leads.get(form_id, [])

    def lead(self, lead_id):
        for items in self.leads.values():
            for item in items:
                if item["id"] == lead_id:
                    return item
        raise MetaError("not found")


@tagged("post_install", "-at_install")
class TestMetaLeads(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Form = self.env["mrj.meta.lead.form"]
        self.Form.search([]).active = False  # forms already in the database stay out of these tests
        self.env["ir.config_parameter"].sudo().set_param(P + "token", "")
        self.tag = self.env["crm.tag"].create({"name": "Meta"})
        self.form = self.Form.create({"name": "Winter form", "form_id": "F1", "tag_ids": [(6, 0, self.tag.ids)]})
        self.Lead = self.env["crm.lead"].with_context(active_test=False)

    def test_import_and_dedupe(self):
        fake = FakeMeta({"F1": [lead("L1")]})
        result = self.Form._mrj_sync(client=fake)
        self.assertIn("OK: 1 new leads, 0 already in CRM", result)
        rec = self.Lead.search([("mrj_meta_lead_id", "=", "L1")])
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec.name, "Winter form: Sara Khan")
        self.assertEqual(rec.contact_name, "Sara Khan")
        self.assertEqual(rec.email_from, "sara@example.com")
        self.assertEqual(rec.country_id.code, "SA")
        self.assertEqual(rec.mrj_meta_campaign, "Winter sale")
        self.assertEqual(rec.mrj_meta_platform, "Instagram")
        self.assertEqual(rec.campaign_id.title, "Winter sale")
        self.assertEqual(rec.source_id.name, "Instagram")
        self.assertEqual(rec.tag_ids, self.tag)
        self.assertIn("&lt;b&gt;please&lt;/b&gt;", str(rec.description), "answers must be escaped")
        self.assertIn("What do you need?", str(rec.description))
        self.assertTrue(self.form.last_lead_time)
        # second run: same lead again, nothing new
        result = self.Form._mrj_sync(client=fake)
        self.assertIn("OK: 0 new leads, 1 already in CRM", result)
        self.assertEqual(self.Lead.search_count([("mrj_meta_lead_id", "=", "L1")]), 1)
        # the second run asks only for leads after the newest one (minus a minute)
        self.assertGreater(fake.calls[1][1], fake.calls[0][1])

    def test_archived_form_skipped_and_errors(self):
        self.form.active = False
        result = self.Form._mrj_sync(client=FakeMeta({"F1": [lead("L2")]}))
        self.assertIn("0 new leads", result)
        self.form.active = True
        result = self.Form._mrj_sync(client=FakeMeta(fail=True))
        self.assertIn("Partly failed", result)
        self.assertIn("access token", result)

    def test_no_token(self):
        self.assertIn("no Page access token", self.Form._mrj_sync())

    def test_first_last_name_and_opportunity(self):
        self.form.lead_type = "opportunity"
        data = lead("L3", field_data=[{"name": "first_name", "values": ["Ali"]}, {"name": "last_name", "values": ["Raza"]}])
        rec = self.env["crm.lead"]._mrj_meta_import(data, self.form)
        self.assertEqual(rec.contact_name, "Ali Raza")
        self.assertEqual(rec.type, "opportunity")

    def test_load_forms(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(P + "page_id", "PAGE")
        icp.set_param(P + "token", "x")
        fake = FakeMeta(forms=[{"id": "F1", "name": "Renamed", "status": "ACTIVE"},
                               {"id": "F2", "name": "Old form", "status": "ARCHIVED"}])
        ok, msg = self.Form._mrj_load_forms(client=fake)
        self.assertTrue(ok, msg)
        self.assertEqual(self.form.name, "Renamed")
        f2 = self.Form.with_context(active_test=False).search([("form_id", "=", "F2")])
        self.assertFalse(f2.active, "archived Meta forms come in switched off")

    def test_client_fallbacks(self):
        from ..models.meta_client import BASIC_FIELDS, MetaClient

        class Resp:
            def __init__(self, status, data):
                self.status_code, self._data, self.text, self.headers = status, data, json.dumps(data), {}

            def json(self):
                return self._data

        class Session:
            def __init__(self):
                self.seen = []

            def get(self, url, params=None, timeout=None):
                self.seen.append(dict(params or {}))
                if "ad_name" in (params or {}).get("fields", ""):
                    return Resp(400, {"error": {"code": 100, "message": "(#100) Tried accessing nonexisting field (ad_name)"}})
                if "filtering" in (params or {}):
                    return Resp(400, {"error": {"code": 100, "message": "(#100) Filtering is not supported"}})
                if (params or {}).get("after"):
                    return Resp(200, {"data": [{"id": "L2"}]})
                return Resp(200, {"data": [{"id": "L1"}], "paging": {"next": "https://graph.facebook.com/v27.0/F1/leads?after=x&access_token=t"}})

        session = Session()
        client = MetaClient("t", session=session)
        # the next link carries its own query, so the fake answers it by URL
        session_get = session.get
        session.get = lambda url, params=None, timeout=None: (
            Resp(200, {"data": [{"id": "L2"}]}) if "after=x" in url else session_get(url, params, timeout))
        leads = client.form_leads("F1", 1700000000)
        self.assertEqual([x["id"] for x in leads], ["L1", "L2"])
        self.assertEqual(client._fields, BASIC_FIELDS)
        bad = MetaClient("t", session=type("S", (), {"get": lambda *a, **k: Resp(400, {"error": {"code": 190, "message": "expired"}})})())
        with self.assertRaises(MetaError) as err:
            bad.form_leads("F1")
        self.assertIn("access token", str(err.exception))

    def test_signature(self):
        body = b'{"a":1}'
        sig = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(signature_ok(body, sig, "secret"))
        self.assertFalse(signature_ok(body, sig, "other"))
        self.assertFalse(signature_ok(body, "", "secret"))
        self.assertFalse(signature_ok(body, sig, ""))


@tagged("post_install", "-at_install")
class TestMetaWebhook(HttpCase):
    def setUp(self):
        super().setUp()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(P + "verify_token", "hello")
        icp.set_param(P + "app_secret", "secret")

    def test_verify_and_bad_signature(self):
        url = "/mrj_meta_leads/webhook"
        ok = self.url_open(url + "?hub.mode=subscribe&hub.verify_token=hello&hub.challenge=12345")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.text, "12345")
        bad = self.url_open(url + "?hub.mode=subscribe&hub.verify_token=nope&hub.challenge=12345")
        self.assertEqual(bad.status_code, 403)
        body = json.dumps({"object": "page", "entry": []}).encode()
        res = self.url_open(url, data=body, headers={"X-Hub-Signature-256": "sha256=0000", "Content-Type": "application/json"})
        self.assertEqual(res.status_code, 403)
        sig = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        res = self.url_open(url, data=body, headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
        self.assertEqual(res.status_code, 200)
