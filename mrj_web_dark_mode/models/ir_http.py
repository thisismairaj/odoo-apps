from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def color_scheme(self):
        """Odoo Community always answers "light"; use the user's choice stored in the color_scheme cookie."""
        if request and request.httprequest.cookies.get("color_scheme") == "dark":
            return "dark"
        return super().color_scheme()
