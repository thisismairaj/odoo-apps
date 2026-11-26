import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

function darkModeItem() {
    return {
        type: "switch",
        id: "mrj_dark_mode.switch",
        description: _t("Dark Mode"),
        callback: () => {
            const dark = cookie.get("color_scheme") === "dark";
            cookie.set("color_scheme", dark ? "light" : "dark");
            browser.location.reload();
        },
        isChecked: cookie.get("color_scheme") === "dark",
        sequence: 30,
    };
}

registry.category("user_menuitems").add("mrj_dark_mode", darkModeItem);
