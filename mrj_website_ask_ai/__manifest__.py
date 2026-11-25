{
    "name": "Ask AI About This Product",
    "summary": "A button on eCommerce product pages that opens the shopper's own AI assistant "
    "(ChatGPT, Perplexity, Claude, Gemini, Grok) with the product link and a buying question filled in.",
    "version": "20.0.1.0.0",
    "category": "Website/eCommerce",
    "author": "Muhammad Mairaj",
    "website": "https://thisismairaj.com",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/templates.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "mrj_website_ask_ai/static/src/css/ask_ai.css",
            "mrj_website_ask_ai/static/src/js/ask_ai.js",
        ],
    },
    "images": ["static/description/main_screenshot.png"],
    "installable": True,
    "application": False,
}
