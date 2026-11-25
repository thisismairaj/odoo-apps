import re
from urllib.parse import quote

from odoo import models
from odoo.tools import html2plaintext

from .res_config_settings import DEFAULT_LABEL, DEFAULT_PROMPT

# (key, label, URL with {q} for the question or "", copy the question first)
ASSISTANTS = [
    ("chatgpt", "ChatGPT", "https://chatgpt.com/?q={q}", False),
    ("perplexity", "Perplexity", "https://www.perplexity.ai/search/new?q={q}", False),
    ("claude", "Claude", "https://claude.ai/new?q={q}", True),
    ("gemini", "Gemini", "https://gemini.google.com/app", True),
    ("grok", "Grok", "https://grok.com/?q={q}", True),
    ("copy", "Copy for any AI", "", True),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _mrj_ask_ai_data(self, website):
        """Values for the Ask AI menu on the product page, or None when every assistant is turned off."""
        self.ensure_one()
        icp = self.env["ir.config_parameter"].sudo()

        def enabled(key):
            # On until the admin turns it off in Settings (Odoo stores the unticked box as False).
            return icp.get_bool("mrj_website_ask_ai." + key, True)

        url = website.get_base_url() + self.website_url
        prompt = icp.get_str("mrj_website_ask_ai.prompt") or DEFAULT_PROMPT
        for placeholder, value in (("{product}", self.name or ""), ("{url}", url), ("{shop}", website.name or "")):
            prompt = prompt.replace(placeholder, value)

        items = []
        for key, label, link, copy_first in ASSISTANTS:
            if enabled(key):
                items.append({
                    "key": key,
                    "label": self.env._("Copy for any AI") if key == "copy" else label,
                    "url": link.replace("{q}", quote(prompt, safe="")) if link else "",
                    "copy_first": copy_first,
                })
        if not items:
            return None

        short = re.sub(r"\s+", " ", html2plaintext(self.description_sale or "")).strip() if self.description_sale else ""
        copy_text = f"{self.name}\n{url}" + (f"\n\n{short}" if short else "") + f"\n\n{prompt}"
        return {
            "label": icp.get_str("mrj_website_ask_ai.label") or self.env._(DEFAULT_LABEL),
            "prompt": prompt,
            "copy": copy_text,
            "items": items,
            "msg_copied": self.env._("Question copied. If the assistant opens empty, paste it in."),
            "msg_copied_all": self.env._("Product details copied. Paste them into any AI."),
        }
