{
    "name": "Calendly Bookings to Calendar",
    "summary": "Bring your Calendly bookings into the Odoo Calendar: invitees as contacts, meeting link, "
    "their answers, and cancellations. Works with Calendly's free plan (no webhooks needed).",
    "version": "18.0.1.0.2",
    "category": "Productivity/Calendar",
    "author": "Softstribe Ventures",
    "website": "https://thisismairaj.com",
    "license": "LGPL-3",
    "depends": ["calendar"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "data/ir_cron.xml",
        "views/res_config_settings_views.xml",
        "views/calendar_event_views.xml",
    ],
    "images": ["static/description/main_screenshot.png"],
    "installable": True,
    "application": False,
}
