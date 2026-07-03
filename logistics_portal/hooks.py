app_name = "logistics_portal"
app_title = "Justyol Logistics"
app_publisher = "Justyol"
app_description = "Logistics-team portal for the Justyol Morocco warehouse floor"
app_email = "info@justyol.com"
app_license = "MIT"

# ---------------------------------------------------------------------------
# Website routing — send every /logistics/* request to the single SPA page.
# ---------------------------------------------------------------------------
website_route_rules = [
    {"from_route": "/logistics/<path:app_path>", "to_route": "logistics"},
]

# ---------------------------------------------------------------------------
# Guest-accessible whitelisted methods (login screen boot only).
# ---------------------------------------------------------------------------
guest_methods = [
    "logistics_portal.api.auth.get_boot",
]

# ---------------------------------------------------------------------------
# Document events
#   - Capture enforcement: no Pick List submitted without an assigned picker.
#   - Stage timestamps: stamp custom_*_at on Sales Order status transitions so
#     time-in-stage and SLA are precise instead of scraped from the Version log.
#   - Packer capture on Delivery Note.
# ---------------------------------------------------------------------------
doc_events = {
    "Pick List": {
        "before_submit": "logistics_portal.api.picking.enforce_picker_on_submit",
        "on_update": "logistics_portal.api.picking.sync_pick_progress",
    },
    "Sales Order": {
        "on_update": "logistics_portal.api.orders.stamp_stage_timestamps",
    },
    "Delivery Note": {
        "validate": "logistics_portal.api.shipping.capture_packer",
    },
}

# ---------------------------------------------------------------------------
# Scheduled jobs — SLA engine + audit rule engine + daily LLM digest.
# ---------------------------------------------------------------------------
scheduler_events = {
    "cron": {
        # SLA engine: recompute expected dates + sla_status every 15 minutes.
        "*/15 * * * *": [
            "logistics_portal.api.sla.run_sla_engine",
        ],
        # Audit rule engine: scan recent docs against thresholds every 10 minutes.
        "*/10 * * * *": [
            "logistics_portal.api.audit.run_rule_engine",
        ],
    },
    "daily_long": [
        # End-of-day narrative digest written by the LLM reviewer.
        "logistics_portal.api.audit.generate_daily_digest",
    ],
}

# ---------------------------------------------------------------------------
# Fixtures — custom fields and roles this portal adds, exported on
# `bench export-fixtures` so they travel with the app.
# ---------------------------------------------------------------------------
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    # Sales Order — precise stage timestamps for SLA / time-in-stage.
                    "Sales Order-custom_picked_at",
                    "Sales Order-custom_labeled_at",
                    "Sales Order-custom_shipped_at",
                    "Sales Order-custom_delivered_at",
                    # Delivery Note — explicit packer/shipper capture.
                    "Delivery Note-custom_assigned_packer",
                    # User — logistics role mapping (Dispatcher/Picker/Packer/Returns/Manager).
                    "User-custom_logistics_role",
                    "User-custom_logistics_zone",
                ],
            ]
        ],
    },
    {
        "dt": "Role",
        "filters": [["name", "in", ["Logistics Portal User"]]],
    },
]
