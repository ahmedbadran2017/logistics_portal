# Catalog Hub — Shopify ⇄ ERPNext catalog reconciliation.
#
# Phase 0 (read-only): sync each item's live Shopify product/variant STATUS into
# ERPNext so ops can see which code is ACTIVE vs archived/draft/deleted — the
# signal that resolves stranded stock and false-OOS. Built as a bounded module
# inside logistics_portal for now; designed to extract into its own app once the
# write-back (Phase 1) makes runtime isolation worth the split.
