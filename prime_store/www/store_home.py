import frappe
from frappe import _

from prime_store.prime_store.doctype.prime_store_settings.prime_store_settings import get_settings
from prime_store.website import HOME_CACHE_PREFIX, get_category_tree, get_products


def get_context(context):
	context.no_cache = 1
	context.full_width = 1
	context.no_breadcrumbs = 1
	context.title = _("Home")

	# Per-client settings live in Prime Store Settings (desk), never in code. Unset means the block is hidden.
	store = get_settings()
	context.announcement = store.announcement
	context.deal_end = store.deal_end
	context.shop_url = store.shop_url

	context.settings = frappe.get_cached_doc("Webshop Settings")
	context.slides = get_slides(store.hero_slideshow) or default_slides(
		context.shop_url
	)
	context.offers = get_slides(store.offers_slideshow)[:2]
	context.update(get_sections())


def get_sections():
	# Pricing every product is the slow part of this page. Guests all see the same prices, so cache
	# their copy briefly (cleared on product/price changes); signed-in users may have their own prices.
	if frappe.session.user != "Guest":
		return build_sections()
	key = f"{HOME_CACHE_PREFIX}{frappe.local.lang}"
	data = frappe.cache.get_value(key)
	if data is None:
		data = build_sections()
		frappe.cache.set_value(key, data, expires_in_sec=300)
	return data


def build_sections():
	products = _safe(get_products, limit=8)
	featured = {p.item_code for p in products}
	return {
		"categories": (_safe(get_category_tree) or [])[:10],
		"products": products,
		"new_arrivals": [p for p in _safe(get_products, limit=12, sort="newest") if p.item_code not in featured][:4],
		"brands": _safe(get_brands),
	}


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
