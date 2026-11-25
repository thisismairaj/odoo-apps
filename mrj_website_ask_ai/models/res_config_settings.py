from odoo import api, fields, models

from ._mrj_compat import bool_get_values, bool_set_values

DEFAULT_PROMPT = (
    'Read {url} ("{product}" from {shop}). Tell me in plain words what this product is, who it suits, '
    "what to check before buying it, and how it compares with similar products. Then help me with my questions."
)
DEFAULT_LABEL = "Ask AI about this product"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mrj_ask_ai_label = fields.Char(
        string="Button text", config_parameter="mrj_website_ask_ai.label", default=DEFAULT_LABEL
    )
    mrj_ask_ai_prompt = fields.Char(
        string="Question",
        config_parameter="mrj_website_ask_ai.prompt",
        default=DEFAULT_PROMPT,
        help="Placeholders: {product}, {url}, {shop}.",
    )
    mrj_ask_ai_chatgpt = fields.Boolean("ChatGPT", default=True)
    mrj_ask_ai_perplexity = fields.Boolean("Perplexity", default=True)
    mrj_ask_ai_claude = fields.Boolean("Claude", default=True)
    mrj_ask_ai_gemini = fields.Boolean("Gemini", default=True)
    mrj_ask_ai_grok = fields.Boolean("Grok", default=True)
    mrj_ask_ai_copy = fields.Boolean("Copy for any AI", default=True)

    _MRJ_BOOLS = {"mrj_ask_ai_%s" % k: ("mrj_website_ask_ai.%s" % k, True)
                  for k in ("chatgpt", "perplexity", "claude", "gemini", "grok", "copy")}

    @api.model
    def get_values(self):
        return bool_get_values(self, super().get_values(), self._MRJ_BOOLS)

    def set_values(self):
        super().set_values()
        bool_set_values(self, self._MRJ_BOOLS)
