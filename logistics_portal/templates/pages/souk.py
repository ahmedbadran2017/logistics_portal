"""Page properties for the portal shell.

no_cache, and the reason is worth writing down.

frappe.website.utils.cache_html caches rendered page HTML in redis keyed by
path — for EVERY user, not only guests. This page is a 2 KB shell whose only
moving part is the <script src> that esbuild stamps with a content hash, so
caching it buys nothing measurable and costs one specific, recurring bug:
deploy, and the cached HTML keeps pointing every browser at the previous
bundle. The app looks unchanged, the server is completely correct, and the
hour goes on finding that out.

It bites whenever `clear-cache` runs before `build` in a deploy — the page is
re-cached against the old asset in the gap between them, and then it sticks
until somebody clears the cache a second time.

Caching this file was never worth a single one of those minutes.
"""

no_cache = 1
