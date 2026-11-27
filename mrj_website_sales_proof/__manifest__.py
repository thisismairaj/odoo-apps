{
    "name": "Honest Sales Popup: Real Recent Orders",
    "summary": "A small social proof popup for your eCommerce shop that only shows the truth: real recent orders, "
    "real product views today and your own trust messages. No fake orders, ever.",
    "version": "18.0.1.0.1",
    "category": "Website/eCommerce",
    "author": "Softstribe Ventures",
    "website": "https://softstribe.com",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/templates.xml",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "mrj_website_sales_proof/static/src/css/sales_proof.css",
            "mrj_website_sales_proof/static/src/js/sales_proof.js",
        ],
    },
    "images": ["static/description/main_screenshot.png"],
    "installable": True,
    "application": False,
}
