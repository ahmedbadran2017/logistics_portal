"""info@justyol.com — phase one: listen, and measure what arrives.

Customers write to info@ with problems and nobody in the portal sees it.
This is the first half of fixing that, and deliberately the half that
changes nothing: the mailbox is connected, Frappe files every message as a
Communication, and NOTHING becomes a CS ticket yet.

Why not go straight to tickets. info@ is a public address: newsletters,
suppliers, Shopify and carrier notifications, invoices, spam, and somewhere
in there the customers. A ticket per message would bury the desk — the same
mistake the AI intake made, 640 tickets in a single day. The filter has to
be written from what actually arrives, and I cannot see that mailbox from
here. So: pull for a few days, run scan(), then write the rules against
real senders instead of an imagined mix.

WHAT THE MEASUREMENT ALREADY SETTLED (production, 2026-10-22)

Matching an email to a customer cannot be done by the sender's address.
Of 18,756 Morocco orders since 1 September:

    orders carrying contact_email .................... 0
    addresses carrying an email ...................... 81 of 26,345
    orders linked to a contact ....................... 4
    orders carrying a phone .......................... 18,751  (99.98%)

38,178 customer emails do exist on Contacts, but only 855 of those 18,756
orders — 4.6% — can be reached from a sender address at all. So the sender
is a tie-breaker, never the key. What the matcher will lean on instead:

    1. an order number in the subject or body. Verified against every order
       name created since 1 August: 27,761 names, _ORDER_RE misses none.
    2. a Moroccan mobile in the body, through the same 9-digit key the CS
       lookup already uses.
    3. the sender, for the one message in twenty where it resolves.

SETTING THE ACCOUNT UP (no code — one Email Account record)

Check two things in Zoho first, because both silently break IMAP:
  - info@ must be a real mailbox or a Shared Mailbox with its own
    credentials. An alias cannot be polled.
  - with 2FA on, generate an application-specific password. The normal
    password is refused.
The IMAP host follows the data centre the organisation is in (imap.zoho.com,
imap.zoho.eu, imap.zoho.in, ...). Read it off the Zoho admin console rather
than guessing — the wrong one fails as a login error.

Then, in Email Account:
    Email ID ................ info@justyol.com
    IMAP server ............. <the host above>      Port 993, SSL on
    Enable incoming ......... yes
    Use IMAP ................ yes
    Default incoming ........ NO
    Append to ............... EMPTY
    Enable auto reply ....... NO

The last three are the ones that do damage. `Default incoming` makes this
account swallow the replies to every other notification the site sends.
`Append to` creates a document per message, which is the flood this phase
exists to avoid. `Enable auto reply` would answer newsletters and spam in
the company's name. health() below checks all three and says so plainly.
"""

import re

import frappe

# Every live order-name shape, verified against 27,761 names created since
# 1 August 2026 with zero misses: "#266577", "J-008094",
# "SAL-ORD-2026-03955", each optionally carrying one or more "-ex" suffixes
# from the exchange flow, and a rare "-1" amendment suffix.
_ORDER_RE = re.compile(
    r"(?:#\s?\d{5,7}|SAL-ORD-\d{4}-\d{4,6}|\bJ-\d{5,7})(?:-\d+)?(?:-ex)*", re.I)

# A customer quoting their order rarely types the '#'. A bare 5-7 digit run
# is far too loose to trust on its own, so it is counted separately and will
# only ever be accepted in phase two after frappe.db.exists confirms it.
_BARE_RE = re.compile(r"(?<!\d)\d{5,7}(?!\d)")

# Moroccan mobile, in any of the three stored shapes (+212…, 0…, 212…). The
# CS lookup's key is the last nine digits; mobiles begin 6 or 7.
_PHONE_RE = re.compile(r"(?:\+?212|0)\s?[67](?:[\s.-]?\d){8}")

# Senders that are machines. Not a filter yet — a label, so scan() can say
# how much of the mailbox is never going to be a customer.
_ROBOT = ("no-reply", "noreply", "no_reply", "donotreply", "do-not-reply",
          "mailer-daemon", "postmaster", "bounce", "notification",
          "notifications", "support@shopify", "newsletter", "mailchimp",
          "sendgrid", "mailgun")


def _is_robot(sender):
    s = (sender or "").lower()
    return any(k in s for k in _ROBOT)


def _domain(sender):
    s = (sender or "").lower()
    return s.rsplit("@", 1)[-1] if "@" in s else "(none)"


# Markup has to go before anything is matched, and this is not tidiness.
# Tested against the 110 real emails on the live account: matching the raw
# body said 105 of them carried an order number. They are newsletters and
# bounce notices — what matched was CSS. "#808080" is six digits behind a
# hash, and so is "#266577". Stripping tags, entities and URLs first takes
# the same corpus from 105 to 18 while still finding "#266577", "J-008094"
# and "SAL-ORD-2026-03955" written in a sentence.
#
# Had this gone out unmeasured, phase two's filter would have been built on
# a signal that fires on every HTML email ever sent.
_TAGS_RE = re.compile(r"(?is)<(script|style)\b.*?</\1>|<[^>]+>")
_ENT_RE = re.compile(r"&[a-z#0-9]{2,8};", re.I)
_URL_RE = re.compile(r"ht" + r"tps?://\S+", re.I)


def _body(r):
    """Subject plus the body as a person typed it — markup removed.

    text_content (the plain-text part) is preferred when the sender provided
    one; it is what they wrote. Falls back to the HTML part stripped."""
    txt = (r.get("text_content") or "") or (r.get("content") or "")
    txt = _TAGS_RE.sub(" ", txt)
    txt = _ENT_RE.sub(" ", txt)
    txt = _URL_RE.sub(" ", txt)
    return ((r.get("subject") or "") + " " + txt)[:6000]


def _account_name(email_id="info@justyol.com"):
    return frappe.db.get_value("Email Account", {"email_id": email_id}, "name")


@frappe.whitelist()
def health(email_id="info@justyol.com"):
    """Is the account set up the way phase one needs it? Read-only."""
    from logistics_portal.api.permissions import require_portal_admin
    require_portal_admin()
    name = _account_name(email_id)
    if not name:
        return {"ok": False, "exists": False,
                "say": f"No Email Account for {email_id} yet."}
    a = frappe.db.get_value(
        "Email Account", name,
        ["enable_incoming", "use_imap", "default_incoming", "append_to",
         "enable_auto_reply", "email_server", "awaiting_password"],
        as_dict=True)
    problems = []
    if not a.enable_incoming:
        problems.append("incoming is off — nothing will be pulled")
    if not a.use_imap:
        problems.append("IMAP is off; POP will not keep the folder in step")
    if a.default_incoming:
        problems.append("DEFAULT INCOMING is on — this account will swallow "
                        "the replies meant for every other one")
    if (a.append_to or "").strip():
        problems.append(f"APPEND TO is set to {a.append_to} — every message "
                        "will create a document, which is the flood phase "
                        "one exists to avoid")
    if a.enable_auto_reply:
        problems.append("AUTO REPLY is on — newsletters and spam will get an "
                        "answer in the company's name")
    if a.awaiting_password:
        problems.append("the password was refused; with 2FA on Zoho needs an "
                        "application-specific password")
    return {"ok": not problems, "exists": True, "account": name,
            "server": a.email_server or "", "problems": problems}


@frappe.whitelist()
def scan(days=7, email_id="info@justyol.com", limit=4000):
    """What is actually arriving — the report that writes phase two's filter.

    Read-only. Never creates, links or answers anything."""
    from logistics_portal.api.permissions import require_portal_admin
    require_portal_admin()
    days = min(max(int(days or 7), 1), 90)
    name = _account_name(email_id)
    if not name:
        return {"ok": False, "say": f"No Email Account for {email_id} yet."}

    rows = frappe.db.sql(
        """SELECT sender, sender_full_name, subject, text_content, content,
                  reference_doctype, reference_name, has_attachment, creation
           FROM `tabCommunication`
           WHERE email_account = %(a)s AND sent_or_received = 'Received'
             AND creation >= DATE_SUB(NOW(), INTERVAL %(d)s DAY)
           ORDER BY creation DESC LIMIT %(l)s""",
        {"a": name, "d": days, "l": min(max(int(limit or 4000), 1), 20000)},
        as_dict=True)

    by_day, senders, domains = {}, {}, {}
    hits = {"order": 0, "bare": 0, "phone": 0, "nothing": 0}
    robots = 0
    samples = {"order": [], "phone": [], "nothing": []}
    for r in rows:
        d = str(r.creation)[:10]
        by_day[d] = by_day.get(d, 0) + 1
        s = (r.sender or "").lower()
        senders[s] = senders.get(s, 0) + 1
        domains[_domain(s)] = domains.get(_domain(s), 0) + 1
        if _is_robot(s):
            robots += 1
        blob = _body(r)
        has_order = bool(_ORDER_RE.search(blob))
        has_phone = bool(_PHONE_RE.search(blob))
        has_bare = bool(_BARE_RE.search(blob))
        if has_order:
            hits["order"] += 1
        if has_phone:
            hits["phone"] += 1
        if has_bare and not has_order:
            hits["bare"] += 1
        key = "order" if has_order else ("phone" if has_phone else "nothing")
        if key == "nothing":
            hits["nothing"] += 1
        if len(samples[key]) < 8:
            samples[key].append({"from": s, "subject": (r.subject or "")[:90]})

    top = lambda d, n: sorted(  # noqa: E731
        ({"k": k, "n": v} for k, v in d.items()), key=lambda x: -x["n"])[:n]
    return {
        "ok": True, "account": name, "days": days, "total": len(rows),
        "perDay": [{"d": k, "n": v} for k, v in sorted(by_day.items())],
        "robots": robots,
        "matchable": hits,
        "topSenders": top(senders, 25),
        "topDomains": top(domains, 20),
        "samples": samples,
        # Said out loud because it is the decision this report exists for.
        "say": ("Of %d received, %d carry an order number and %d a Moroccan "
                "phone; %d carry neither and %d come from a machine. Phase "
                "two's filter should be written from the sender list above, "
                "not from a guess." % (len(rows), hits["order"], hits["phone"],
                                       hits["nothing"], robots)),
    }
