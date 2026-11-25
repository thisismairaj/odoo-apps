"""Settings helpers for Odoo 18.0: ir.config_parameter has only get_param/set_param here.

An unticked Boolean with config_parameter deletes the parameter in Odoo 18.0, so a box that is
on by default would come back ticked. Those booleans are stored as "1"/"0" by the settings model.
"""


def icp_str(icp, key, default=""):
    value = icp.get_param(key)
    return default if value in (None, False) else value


def icp_int(icp, key, default=0):
    try:
        return int(icp.get_param(key) or default)
    except (TypeError, ValueError):
        return default


def icp_bool(icp, key, default=False):
    value = icp.get_param(key)
    if value in (None, False):
        return default
    return str(value).strip().lower() not in ("", "0", "false")


def bool_get_values(settings, res, bools):
    icp = settings.env["ir.config_parameter"].sudo()
    for field, (key, default) in bools.items():
        res[field] = icp_bool(icp, key, default)
    return res


def bool_set_values(settings, bools):
    icp = settings.env["ir.config_parameter"].sudo()
    for field, (key, _default) in bools.items():
        icp.set_param(key, "1" if settings[field] else "0")
