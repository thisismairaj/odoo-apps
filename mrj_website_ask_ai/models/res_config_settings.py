from odoo import fields, models

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
    mrj_ask_ai_chatgpt = fields.Boolean("ChatGPT", config_parameter="mrj_website_ask_ai.chatgpt", default=True)
    mrj_ask_ai_perplexity = fields.Boolean("Perplexity", config_parameter="mrj_website_ask_ai.perplexity", default=True)
    mrj_ask_ai_claude = fields.Boolean("Claude", config_parameter="mrj_website_ask_ai.claude", default=True)
    mrj_ask_ai_gemini = fields.Boolean("Gemini", config_parameter="mrj_website_ask_ai.gemini", default=True)
    mrj_ask_ai_grok = fields.Boolean("Grok", config_parameter="mrj_website_ask_ai.grok", default=True)
    mrj_ask_ai_copy = fields.Boolean("Copy for any AI", config_parameter="mrj_website_ask_ai.copy", default=True)
