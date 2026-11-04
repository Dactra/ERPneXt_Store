import frappe

from prime_store.api import get_compare_items
from prime_store.prime_store.doctype.prime_store_settings.prime_store_settings import get_settings

# /compare?items=CODE1,CODE2 — the list lives in the visitor's browser (prime_store.js) and is
# passed in the URL, so the page also works as a shareable link.
sitemap = 0
no_cache = 1


def get_context(context):
	if not get_settings().enable_compare:
		raise frappe.PageDoesNotExistError
	context.no_cache = 1
	context.body_class = "product-page"
	context.parents = [{"name": frappe._("Home"), "route": "/"}]
	codes = [c.strip() for c in (frappe.form_dict.get("items") or "").split(",")]
	context.items, context.attributes = get_compare_items(codes)
	context.settings = frappe.get_cached_doc("Webshop Settings")
	context.metatags = {"robots": "noindex"}
