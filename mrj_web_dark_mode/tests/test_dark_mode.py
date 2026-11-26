from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDarkMode(HttpCase):
    def _webclient_html(self, dark):
        self.authenticate("admin", "admin")
        if dark:
            self.opener.cookies.set("color_scheme", "dark")
        res = self.url_open("/odoo")
        self.assertEqual(res.status_code, 200)
        return res.text

    def test_light_by_default(self):
        self.assertNotIn("web.assets_web_dark", self._webclient_html(dark=False))

    def test_dark_bundle_with_cookie(self):
        self.assertIn("web.assets_web_dark", self._webclient_html(dark=True))
