"""Backfill missing Item images from Shopify.

The Morocco external integration creates Items (owner "Guest") with an empty
`image`, so pickers see a placeholder where the product photo should be —
26,202 catalog items had no image at discovery, 158 of them picked in August.
Every one of the sampled gaps was ee-mapped, i.e. the photo already exists on
our own Shopify store; this pulls the variant image (or the product's featured
image) and stores its CDN URL on the Item. db.set_value only — no ERPNext
save-side effects, nothing is pushed back to Shopify.
"""

import json

import frappe

_IMG_QUERY = """
query($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on ProductVariant {
      id
      image { url }
      product { featuredImage { url } }
    }
  }
}
"""


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can backfill images.", frappe.PermissionError)


# Items with no image, joined to their Shopify variant, hottest first (items
# on recent pick lists get their photos before the long tail).
_GAP_FROM = """
    FROM `tabItem` i
    JOIN `tabEcommerce Item` ei ON ei.erpnext_item_code = i.name
         AND COALESCE(ei.variant_id, '') <> ''
    WHERE COALESCE(i.image, '') = '' AND i.disabled = 0
"""

_HOT = """
    (SELECT COUNT(*) FROM `tabPick List Item` pli
     JOIN `tabPick List` pl ON pl.name = pli.parent
     WHERE pli.item_code = i.name
       AND pl.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY))
"""


@frappe.whitelist()
def image_gaps():
    """How many items lack a photo, and how many of those we can fix from
    Shopify (ee-mapped) — including the ones pickers actually see."""
    _gate()
    fixable = frappe.db.sql(f"SELECT COUNT(*) {_GAP_FROM}")[0][0]
    hot = frappe.db.sql(
        f"SELECT COUNT(*) {_GAP_FROM} AND {_HOT} > 0")[0][0]
    total = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabItem`
           WHERE COALESCE(image,'') = '' AND disabled = 0""")[0][0]
    return {"missingTotal": int(total or 0), "fixable": int(fixable or 0),
            "hot": int(hot or 0)}


@frappe.whitelist()
def backfill_images(limit=100):
    """Fill up to `limit` missing images from Shopify, hottest items first.
    Returns how many were filled, how many variants had no photo on Shopify
    either, and how many are left."""
    from logistics_portal.api.catalog_hub.sync import shopify_graphql
    _gate()
    limit = min(max(int(limit or 100), 1), 500)
    # Variants Shopify itself has no photo for would win the "hottest" sort
    # every run and wedge the queue — skip the ones seen photo-less today.
    cache = frappe.cache()
    skip = set(json.loads(cache.get_value("lp_img_nophoto") or "[]"))
    rows = frappe.db.sql(
        f"""SELECT i.name AS item, ei.variant_id
            {_GAP_FROM}
            ORDER BY {_HOT} DESC, i.modified DESC LIMIT %s""",
        (limit + len(skip),), as_dict=True)
    rows = [r for r in rows if r.item not in skip][:limit]
    if not rows:
        return {"filled": 0, "noPhoto": 0, "failed": 0, "remaining": 0}

    by_gid = {}
    for r in rows:
        by_gid[f"gid://shopify/ProductVariant/{r.variant_id}"] = r.item

    filled, no_photo, failed = 0, 0, 0
    gids = list(by_gid)
    for i in range(0, len(gids), 50):
        chunk = gids[i:i + 50]
        try:
            data = shopify_graphql(_IMG_QUERY, {"ids": chunk})
        except Exception:
            failed += len(chunk)
            frappe.log_error(frappe.get_traceback(), "catalog_hub.backfill_images")
            continue
        for node in (data.get("data") or {}).get("nodes") or []:
            if not node:
                continue
            item = by_gid.get(node.get("id"))
            if not item:
                continue
            url = ((node.get("image") or {}).get("url")
                   or ((node.get("product") or {}).get("featuredImage") or {}).get("url") or "")
            if url:
                frappe.db.set_value("Item", item, "image", url,
                                    update_modified=False)
                filled += 1
            else:
                no_photo += 1
                skip.add(item)
    cache.set_value("lp_img_nophoto", json.dumps(sorted(skip)),
                    expires_in_sec=86400)
    frappe.db.commit()
    remaining = frappe.db.sql(f"SELECT COUNT(*) {_GAP_FROM}")[0][0]
    return {"filled": filled, "noPhoto": no_photo, "failed": failed,
            "remaining": int(remaining or 0)}
