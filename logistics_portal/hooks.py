from . import __version__ as app_version  # noqa: F401

app_name = "logistics_portal"
app_title = "Logistics Portal"
app_publisher = "Justyol"
app_description = "Logistics & Warehouse operations portal for the Justyol team"
app_email = "info@justyol.com"
app_license = "MIT"

# Website route rules — serve the Vue SPA for every /logistics/* path.
website_route_rules = [
    {"from_route": "/logistics/<path:app_path>", "to_route": "logistics"},
    {"from_route": "/logistics", "to_route": "logistics"},
]

# Install / Migrate hooks
after_install = "logistics_portal.install.after_install"
after_migrate = [
    "logistics_portal.install._create_portal_roles",
]
