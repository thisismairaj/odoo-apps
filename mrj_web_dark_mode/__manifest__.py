{
    "name": "Dark Mode for Community",
    "summary": "A dark theme for the Odoo Community backend, switched on per user from the user menu. "
    "No configuration, no external files.",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "Muhammad Mairaj",
    "website": "https://thisismairaj.com",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "mrj_web_dark_mode/static/src/js/dark_mode_switch.js",
        ],
        "web.assets_web_dark": [
            ("prepend", "mrj_web_dark_mode/static/src/scss/primary_variables.dark.scss"),
            "mrj_web_dark_mode/static/src/scss/dark_overrides.dark.scss",
        ],
    },
    "images": ["static/description/main_screenshot.png"],
    "installable": True,
    "application": False,
}
