"""Post-migrate setup: performance indexes the board queries depend on.

The portal filters Sales Orders by custom status fields and anti-joins Pick
List Items on every board request; without these indexes each request scans
30k+ rows (~4-8s measured on the live bench — 0.3-0.6s after indexing).
frappe.db.add_index is idempotent, so this is safe to run on every migrate.
"""

import frappe


INDEXES = [
    ("Sales Order", ["custom_logistics_status", "custom_sales_status"], "lp_logistics_status_idx"),
    ("Pick List Item", ["sales_order"], "lp_pli_so_idx"),
    ("Delivery Note Item", ["against_sales_order"], "lp_dni_so_idx"),
    ("Delivery Note", ["custom_track_shipment_status"], "lp_dn_track_idx"),
    # SKU lookup scans 151k Items by custom_sku — index it.
    ("Item", ["custom_sku"], "lp_item_sku_idx"),
    # Cockpit breach counts / breached_list / the 10-min audit engine all
    # filter DNs by SLA status within a posting window.
    ("Delivery Note", ["custom_sla_status", "posting_date"], "lp_dn_sla_idx"),
    # manifest_scan / ready-parcels NOT-IN / shipped-stage rows join on the
    # child table's delivery_note (parent is indexed by default; this isn't).
    ("Shipment Delivery Note", ["delivery_note"], "lp_sdn_dn_idx"),
    # Board counts + intake filter Confirmed orders by creation window.
    ("Sales Order", ["custom_sales_status", "creation"], "lp_so_sales_creation_idx"),
    # Contact Center my-day tallies filter Comments by owner+today, and the
    # section reports scan by doctype+window. tabComment is 2.6M rows with no
    # index on either — measured 31s per board load on the live site without
    # these.
    ("Comment", ["owner", "creation"], "lp_comment_owner_idx"),
    ("Comment", ["reference_doctype", "creation"], "lp_comment_dt_idx"),
    # manifest_scan matches a scanned parcel by AWB. Neither column is a Link,
    # so Frappe indexes neither — every scan was a full 119k Delivery Note scan
    # with an operator standing at the handover station waiting for it.
    ("Delivery Note", ["custom_awb"], "lp_dn_awb_idx"),
    ("Delivery Note", ["custom_tracking_number"], "lp_dn_track_no_idx"),
    # The confirmation board's "done" tabs (Confirmed / Cancelled /
    # Duplicated). An agent sees their OWN decisions, so every one of the
    # three queries a tab runs is fenced on custom_allocated_to — a column
    # with no index at all, over 265,656 rows. Measured 2026-09-09 on prod:
    # the row page cost 1,061 ms for 20 rows, the total 322 ms (type=ALL,
    # full table scan) and the tab counts 1,079 ms — 2.0 s of a 2.2 s board
    # load. The last two columns let the decision window be read straight
    # from the index (see confirmation._decided).
    ("Sales Order",
     ["custom_allocated_to", "custom_sales_status", "custom_last_call_at", "modified"],
     "lp_so_agent_status_idx"),
    # The same tabs in the TEAM scope (manager / section admin) date strictly
    # on custom_last_call_at, which is set on 67 rows of the 265,656 — and
    # without an index the board still read all of them. lp_so_sales_creation
    # _idx carries `creation` as its second column, so it cannot serve this.
    ("Sales Order", ["custom_sales_status", "custom_last_call_at"],
     "lp_so_sales_lastcall_idx"),
    # My Dashboard reads each agent's decision trail out of `tabVersion` —
    # the desk writes a Version row and no comment, so the Version trail is
    # the only record of half the decisions. That table is 2.95M rows and
    # 4.1 GB with nothing indexed but (ref_doctype, docname) and `modified`,
    # so a filter on owner+creation had no way in: MariaDB drove the join
    # from `tabSales Order` instead, full-scanning 206,676 orders and probing
    # 4 GB of versions to return 718 rows. Measured 2026-09-09: 7.1s of an
    # 8.8s call, and the page makes TWO of them (this period and the one
    # before), so opening My Dashboard cost the better part of twenty
    # seconds. NB: adding this index rewrites a 4 GB table — run the migrate
    # off-peak.
    ("Version", ["owner", "ref_doctype", "creation"], "lp_version_owner_idx"),
    # The CC team-activity board slices ONE DAY of Sales Order versions with
    # no owner in hand (the owner set is what it is trying to discover). The
    # (ref_doctype, docname) core index cannot serve a creation range, so the
    # day read full-scanned ~3M rows — measured 6.8s. This turns it into a
    # range scan. Same off-peak caveat as the owner index: it rewrites a big
    # table once.
    ("Version", ["ref_doctype", "creation"], "lp_version_day_idx"),
    # The scan witness log: every activity question slices on person-over-time
    # or station-over-time. (Created by scanlog.ensure_doctype, which hooks.py
    # runs in the same after_migrate pass; add_index is try/except, so the
    # very first migrate simply picks these up on its second run.)
    ("LP Scan Event", ["owner", "creation"], "lp_scan_owner_idx"),
    ("LP Scan Event", ["station", "creation"], "lp_scan_station_idx"),
]


def ensure_indexes():
    for doctype, fields, name in INDEXES:
        try:
            frappe.db.add_index(doctype, fields, index_name=name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"logistics_portal.ensure_indexes {doctype}")


# Catalog Hub status fields on Item — populated by catalog_hub.sync (read-only
# mirror of the live Shopify product/variant state).
_CATALOG_FIELDS = [
    {"fieldname": "custom_shopify_status", "label": "Shopify Status", "fieldtype": "Data",
     "read_only": 1, "no_copy": 1, "in_standard_filter": 1,
     "description": "ACTIVE / ARCHIVED / DRAFT / DELETED / UNMAPPED — mirrored from Shopify by Catalog Hub"},
    {"fieldname": "custom_variant_live", "label": "Shopify Variant Live", "fieldtype": "Check",
     "read_only": 1, "no_copy": 1,
     "description": "1 if this item's Shopify variant still exists"},
    {"fieldname": "custom_shopify_synced_on", "label": "Shopify Status Synced On",
     "fieldtype": "Datetime", "read_only": 1, "no_copy": 1},
]


def ensure_catalog_fields():
    """Create the Catalog Hub status fields on Item (idempotent)."""
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields({"Item": _CATALOG_FIELDS}, ignore_validate=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.ensure_catalog_fields")


# Scan-to-pick progress: how many units of a Pick List line the picker has
# scanned off the shelf (persisted so it survives a reload / device switch).
_PLI_FIELDS = [
    {"fieldname": "custom_scanned_qty", "label": "Scanned Qty", "fieldtype": "Int",
     "default": "0", "read_only": 1, "no_copy": 1, "in_list_view": 0},
    # Sorting-station progress: units of this line allocated to its order at
    # the sort wall (independent of the shelf-side custom_scanned_qty).
    {"fieldname": "custom_sorted_qty", "label": "Sorted Qty", "fieldtype": "Int",
     "default": "0", "read_only": 1, "no_copy": 1, "in_list_view": 0},
]


_DN_EXC_FIELDS = [
    # Exceptions triage: the recorded decision per failed parcel. Turns the
    # exceptions pile into a worked queue (who decided what, when).
    {"fieldname": "custom_exception_action", "label": "Exception Action",
     "fieldtype": "Select", "options": "\nRedeliver\nReturn Requested\nResolved",
     "read_only": 1, "no_copy": 1, "hidden": 1},
    {"fieldname": "custom_exception_actioned_at", "label": "Exception Actioned At",
     "fieldtype": "Datetime", "read_only": 1, "no_copy": 1, "hidden": 1},
]

# Contact Center lane 3 — CS tickets ride the stock ERPNext Issue doctype;
# these fields tie a ticket to the COD reality (phone, order, channel, agent).
_ISSUE_FIELDS = [
    {"fieldname": "custom_phone", "label": "Customer Phone", "fieldtype": "Data",
     "in_standard_filter": 1, "no_copy": 1},
    {"fieldname": "custom_order", "label": "Sales Order", "fieldtype": "Data", "no_copy": 1},
    {"fieldname": "custom_channel", "label": "Channel", "fieldtype": "Select",
     "options": "\nwhatsapp\nphone\nmanual", "no_copy": 1},
    {"fieldname": "custom_category", "label": "Category", "fieldtype": "Data", "no_copy": 1},
    {"fieldname": "custom_agent", "label": "Agent", "fieldtype": "Data", "no_copy": 1},
]

# Inbox marker on the third-party WhatsApp Message doctype: which incoming
# messages the CS lane has already turned into tickets / dismissed.
_WA_FIELDS = [
    {"fieldname": "custom_lp_handled", "label": "LP Handled", "fieldtype": "Check",
     "default": "0", "read_only": 1, "no_copy": 1, "hidden": 1},
]


def ensure_cs_fields():
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        payload = {"Issue": _ISSUE_FIELDS}
        if frappe.db.exists("DocType", "WhatsApp Message"):
            payload["WhatsApp Message"] = _WA_FIELDS
        create_custom_fields(payload, ignore_validate=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.ensure_cs_fields")


_SO_CONTACT_FIELDS = [
    # Contact Center (confirmation lane): when the call happened, how many
    # times, and when to retry. The WhatsApp automation stays first-line;
    # these track the human tail it can't close.
    # NB: WHO owns the order is custom_allocated_to — an existing Link->User
    # field the business already runs on (17 agents live on it, the desk's
    # confirmation dashboard reports off it). Do not add a second one.
    {"fieldname": "custom_call_attempts", "label": "Call Attempts", "fieldtype": "Int",
     "default": "0", "read_only": 1, "no_copy": 1, "hidden": 1},
    {"fieldname": "custom_last_call_at", "label": "Last Call At", "fieldtype": "Datetime",
     "read_only": 1, "no_copy": 1, "hidden": 1},
    {"fieldname": "custom_next_call_at", "label": "Next Call At", "fieldtype": "Datetime",
     "read_only": 1, "no_copy": 1, "hidden": 1},
]

_SO_SHORT_FIELDS = [
    # Set when a picker reports the item physically missing (short pick):
    # batching skips the order for 24h so it doesn't bounce straight back
    # onto the next pick list while the shelf is still empty.
    {"fieldname": "custom_short_picked_at", "label": "Short Picked At",
     "fieldtype": "Datetime", "read_only": 1, "no_copy": 1, "hidden": 1},
]


def ensure_pick_fields():
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields({"Pick List Item": _PLI_FIELDS,
                              "Sales Order": _SO_SHORT_FIELDS + _SO_CONTACT_FIELDS,
                              "Delivery Note": _DN_EXC_FIELDS}, ignore_validate=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.ensure_pick_fields")


def ensure_desk_override_role():
    """The per-user escape valve for the Desk block (api/deskguard): an admin
    grants 'Logistics Desk Override' to hand a team member the Desk back for a
    genuine one-off, and revokes it to re-lock. desk_access=1 so holding it is
    what actually restores Desk access. Idempotent."""
    try:
        if not frappe.db.exists("Role", "Logistics Desk Override"):
            frappe.get_doc({
                "doctype": "Role", "role_name": "Logistics Desk Override",
                "desk_access": 1, "disabled": 0,
            }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.ensure_desk_override_role")


def ensure_role_field_options():
    """Keep the User.custom_logistics_role Select in step with VALID_ROLES —
    the contact-center split added `cs` and `tracking` (2026-08-27), and the
    field still carried only the floor roles, so the Desk's own form (and any
    doc-level save) would reject the new values."""
    import frappe
    wanted = "\nmanager\ndispatcher\npicker\npacker\nreturns\nconfirmation\ncs\ntracking\nnone"
    cf = frappe.db.get_value(
        "Custom Field", {"dt": "User", "fieldname": "custom_logistics_role"},
        ["name", "options"], as_dict=True)
    if cf and (cf.options or "") != wanted:
        frappe.db.set_value("Custom Field", cf.name, "options", wanted,
                            update_modified=False)
        frappe.clear_cache(doctype="User")


def ensure_pick_field_lengths():
    """Widen Pick List Item.item_name so a long product title cannot shatter a
    batch.

    Frappe REFUSES to store a value longer than the column instead of
    truncating it (CharacterLengthExceededError), and the field is a Data with
    no explicit length — so 140 characters. This catalogue has 2,851 items
    whose name is longer than that (longest 222), and on 2026-08-31 a single
    one of them on a combined pick list threw at insert, which dropped the
    whole batch to the one-list-per-order fallback.

    Pre-trimming the value on our side does nothing: item_name is fetch_from
    item_code.item_name with fetch_if_empty = 0, so _validate_links writes the
    full name back over ours (measured: 140 in, 185 out). The only place the
    limit can be raised is the field itself, via a Property Setter — which is
    the supported way to customise a core doctype, and which `bench migrate`
    turns into the matching column ALTER.
    """
    want = 250          # longest name in the catalogue today is 222
    try:
        meta = frappe.get_meta("Pick List Item")
        df = meta.get_field("item_name")
        if not df or int(df.length or 0) >= want:
            return
        frappe.make_property_setter({
            "doctype": "Pick List Item",
            "fieldname": "item_name",
            "property": "length",
            "value": want,
            "property_type": "Int",
        }, is_system_generated=True)
        frappe.clear_cache(doctype="Pick List Item")
    except Exception:
        # Never block a migrate on a cosmetic widening.
        frappe.log_error(frappe.get_traceback()[:2000],
                         "logistics_portal.ensure_pick_field_lengths")
