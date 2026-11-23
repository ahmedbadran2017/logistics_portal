"""Site default rows written without wiping the site cache.

`frappe.db.set_default(key, value)` with a changed value ends in
`frappe.defaults._clear_cache("__default")`, and for the common parents
("__default", "__global") that is `frappe.clear_cache()`: every key of the site
in Redis goes (warm boards, permissions, document cache, job states). A usage
counter bumped after each AI call was enough to delete the result that call had
just stored.

`set_default` here writes the same DefaultValue rows and drops only the one
cached hash that reads them, so `frappe.db.get_default` stays correct.
"""

import frappe


def set_default(key, value, parent="__default"):
    """Drop-in for frappe.db.set_default (same rows, same reads), minus the
    site-wide cache clear. value None deletes the key."""
    value = None if value is None else str(value)
    rows = frappe.db.get_values("DefaultValue", {"parent": parent, "defkey": key},
                                ["name", "defvalue"], as_dict=True)
    if len(rows) == 1 and value is not None and rows[0].defvalue == value:
        return
    if rows:
        frappe.db.delete("DefaultValue", {"parent": parent, "defkey": key})
    if value is not None:
        frappe.get_doc({
            "doctype": "DefaultValue",
            "parent": parent,
            "parenttype": "__default",
            "parentfield": "system_defaults",
            "defkey": key,
            "defvalue": value,
        }).insert(ignore_permissions=True)
    frappe.cache().hdel("defaults", parent)


def get_row(key, parent):
    """One row, straight from the table (no defaults hash). For rows kept under
    their own parent so they never load into the site-wide defaults."""
    return frappe.db.get_value("DefaultValue", {"parent": parent, "defkey": key}, "defvalue")
