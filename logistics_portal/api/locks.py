"""Named DB locks for check-then-act endpoints (manifest close, order merge).

MariaDB GET_LOCK serializes across ALL app workers — a plain Python lock
wouldn't, since gunicorn runs multiple processes. Locks are re-entrant per
connection and auto-released if the connection dies mid-request."""

from contextlib import contextmanager

import frappe


@contextmanager
def named_lock(name, timeout=10):
    got = frappe.db.sql("SELECT GET_LOCK(%s, %s)", (f"lp_{name}", timeout))[0][0]
    if not got:
        frappe.throw("Another device is doing this right now — try again in a moment.")
    try:
        yield
    finally:
        try:
            frappe.db.sql("SELECT RELEASE_LOCK(%s)", (f"lp_{name}",))
        except Exception:
            pass  # connection death releases the lock anyway
