{
    "name": "Facebook and Instagram Lead Ads to CRM",
    "summary": "Bring Meta Lead Ads (Facebook and Instagram instant forms) into Odoo CRM as leads, every 15 "
    "minutes or in real time by webhook. Per-form sales team, salesperson and tags. No duplicates.",
    "version": "19.0.1.0.0",
    "category": "Sales/CRM",
    "author": "Muhammad Mairaj",
    "website": "https://thisismairaj.com",
    "license": "LGPL-3",
    "depends": ["crm"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/meta_lead_form_views.xml",
        "views/crm_lead_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/main_screenshot.png"],
    "installable": True,
    "application": False,
}
