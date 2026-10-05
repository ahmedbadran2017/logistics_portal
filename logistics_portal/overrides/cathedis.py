"""Cathedis AWB: a prepaid order is printed with nothing to collect.

ecommerce_integrations builds the Cathedis payload with

    amount = grand_total - advance_paid      (CathedisShipping.get_*cash_on_delivery_amount)

and never looks at how the customer paid. `paymentType` follows the amount:
"0.0" goes out as PAYE, anything else as ESPECES — measured on #262346's real
Delivery Note, 2026-10-05.

A Payzone Maroc order is paid by card on the site, but nothing records that
in ERPNext before the label: accounting posts the Payzone payment by hand,
usually days after the parcel has left (#245956: AWB 07-02, payment 07-27).
So advance_paid is 0 when the AWB is made, the label asks the courier to
collect the full price, and the customer is charged a second time at the
door. Since July all 32 Payzone orders went out that way; on the ones whose
invoices are reconciled, the Cathedis remittance paid the invoice on top of
the Payzone payment (#245956: 196 via Payzone and 196 via Cathedis).

The fix belongs in ecommerce_integrations; until it lands there, this
replaces those two amounts for prepaid orders, and only for them. Every
other order goes through the original method untouched.

Applied on import. The pick-list background job that creates the AWBs loads
the Pick List controller first, which imports logistics_portal.overrides —
so the patch is in place in that worker before CathedisShipping runs. The
portal's own relabel paths import this module explicitly.
"""

import frappe

# How the customer paid, as Shopify writes it on Sales Order.payment_type.
# Bank transfer ("Virement bancaire") is NOT here: accounting must see the
# money first. Those orders are held out of picking until the transfer is
# posted on the order (picking._TRANSFER_HELD); advance_paid then covers the
# price and the label reads 0 by the integration's own arithmetic.
PREPAID = ("Payzone Maroc",)
ZERO = "0.0"  # the exact string the original returns for nothing to collect


def _is_prepaid(sales_order):
    if not sales_order:
        return False
    pt = (sales_order.get("payment_type") if hasattr(sales_order, "get")
          else frappe.db.get_value("Sales Order", sales_order, "payment_type"))
    return (pt or "") in PREPAID


def _note(so_name, amount):
    try:
        frappe.get_doc({
            "doctype": "Comment", "comment_type": "Comment",
            "reference_doctype": "Sales Order", "reference_name": so_name,
            "content": f"Cathedis AWB amount set to 0 (was {amount}): already paid — "
                       "nothing to collect at the door.",
        }).insert(ignore_permissions=True)
    except Exception:
        pass


def apply():
    try:
        from ecommerce_integrations.shipping.cathedis import CathedisShipping as C
    except Exception:
        return
    if getattr(C, "_lp_prepaid_zero", False):
        return
    orig_dn = C.get_delivery_note_cash_on_delivery_amount
    orig_so = C.get_cash_on_delivery_amount

    def _settle(amount, so_name, prepaid):
        # Prepaid: nothing to collect. Otherwise a remainder under 1 MAD is the
        # rounding of a payment posted in whole dirhams (a 186.10 order paid
        # 186) — collecting 0.10 at the door would print it as cash on
        # delivery; it is paid.
        try:
            dust = 0 < float(amount) < 1
        except (TypeError, ValueError):
            dust = False
        if (prepaid or dust) and str(amount) != ZERO:
            _note(so_name, amount)
            return ZERO
        return amount

    def get_delivery_note_cash_on_delivery_amount(self, delivery_note):
        amount = orig_dn(self, delivery_note)
        so = next((i.against_sales_order for i in (delivery_note.get("items") or [])
                   if i.get("against_sales_order")), None)
        return _settle(amount, so, _is_prepaid(so)) if so else amount

    def get_cash_on_delivery_amount(self, sales_order):
        amount = orig_so(self, sales_order)
        return _settle(amount, sales_order.name, _is_prepaid(sales_order))

    C.get_delivery_note_cash_on_delivery_amount = get_delivery_note_cash_on_delivery_amount
    C.get_cash_on_delivery_amount = get_cash_on_delivery_amount
    C._lp_prepaid_zero = True


apply()
