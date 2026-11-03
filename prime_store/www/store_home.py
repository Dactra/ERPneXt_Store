import frappe
from frappe import _

from prime_store.website import get_categories, get_products


def get_context(context):
	context.no_cache = 1
	context.full_width = 1
	context.no_breadcrumbs = 1
	context.title = _("Home")

	# Per-client settings live in site_config.json, never in code. Unset means the block is hidden.
	context.announcement = frappe.conf.get("prime_store_announcement")
	context.deal_end = frappe.conf.get("prime_store_deal_end")  # e.g. "2026-12-31T23:59:00"
	context.shop_url = frappe.conf.get("prime_store_shop_url") or "/all-products"

	context.settings = frappe.get_cached_doc("Webshop Settings")
	context.slides = get_slides(frappe.conf.get("prime_store_slideshow") or "Home Hero") or default_slides(
		context.shop_url
	)
	context.offers = get_slides(frappe.conf.get("prime_store_offers_slideshow") or "Home Offers")[:2]
	context.categories = _safe(get_categories, 8)
	context.products = _safe(get_products, limit=8)
	featured = {p.item_code for p in context.products}
	context.new_arrivals = [
		p for p in _safe(get_products, limit=12, sort="newest") if p.item_code not in featured
	][:4]
	context.brands = _safe(get_brands)


def _safe(fn, *args, **kwargs):
	try:
		return fn(*args, **kwargs)
	except Exception:
		frappe.log_error(title="Prime Store: homepage data")
		return []


def get_slides(name):
	"""Slides come from a Website Slideshow, so clients edit them from the UI."""
	if not frappe.db.exists("Website Slideshow", name):
		return []
	doc = frappe.get_cached_doc("Website Slideshow", name)
	return [
		{"image": row.image, "heading": row.heading, "description": row.description, "url": row.url}
		for row in doc.slideshow_items
		if row.heading or row.image
	]


def default_slides(shop_url):
	return [
		{"heading": _("Power for every day"), "description": _("Phones, laptops and accessories in one place."), "url": shop_url},
		{"heading": _("Best in gaming"), "description": _("Laptops, consoles and accessories."), "url": shop_url},
		{"heading": _("Sound that moves you"), "description": _("Headphones and speakers for every budget."), "url": shop_url},
	]


def get_brands():
	"""Only brands that have published products, so every brand link shows results."""
	used = frappe.get_all(
		"Website Item", filters={"published": 1, "brand": ["is", "set"]}, pluck="brand", distinct=True
	)
	if not used:
		return []
	return frappe.get_all(
		"Brand", filters={"name": ["in", used]}, fields=["name", "image"], order_by="name asc", limit=12
	)
