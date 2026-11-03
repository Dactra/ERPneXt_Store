import frappe
from frappe import _
from frappe.utils import fmt_money


def get_context(context):
	context.no_cache = 1
	context.full_width = 1
	context.no_breadcrumbs = 1
	context.title = _("Home")

	# Per-client settings live in site_config.json, never in code.
	context.announcement = frappe.conf.get("prime_store_announcement") or _("Big deals this week")
	context.deal_end = frappe.conf.get("prime_store_deal_end")  # e.g. "2026-12-31T23:59:00"
	context.shop_url = frappe.conf.get("prime_store_shop_url") or "/all-products"

	context.slides = get_slides(context.shop_url)
	context.categories = _safe(get_categories)
	context.products = _safe(get_products)
	context.brands = _safe(get_brands)


def _safe(fn):
	try:
		return fn()
	except Exception:
		frappe.log_error(title="Prime Store: homepage data")
		return []


def get_slides(shop_url):
	"""Slides come from a Website Slideshow named 'Home Hero', so clients edit them from the UI."""
	name = frappe.conf.get("prime_store_slideshow") or "Home Hero"
	if frappe.db.exists("Website Slideshow", name):
		doc = frappe.get_doc("Website Slideshow", name)
		slides = [
			{
				"image": row.image,
				"heading": row.heading,
				"description": row.description,
				"url": row.url or shop_url,
			}
			for row in doc.slideshow_items
		]
		if slides:
			return slides

	return [
		{"heading": _("Power for every day"), "description": _("New devices, delivered fast."), "url": shop_url},
		{"heading": _("Best in gaming"), "description": _("Laptops, consoles and accessories."), "url": shop_url},
		{"heading": _("Sound that moves you"), "description": _("Headphones and speakers on sale."), "url": shop_url},
	]


def get_categories():
	return frappe.get_all(
		"Item Group",
		filters={"show_in_website": 1, "is_group": 0},
		fields=["name", "route", "image"],
		order_by="modified desc",
		limit=8,
	)


def get_products():
	items = frappe.get_all(
		"Website Item",
		filters={"published": 1},
		fields=["name", "item_code", "web_item_name", "route", "website_image", "brand"],
		order_by="ranking desc, modified desc",
		limit=8,
	)
	price_list = frappe.db.get_single_value("Webshop Settings", "price_list")
	for item in items:
		item.price = None
		if not price_list:
			continue
		price = frappe.db.get_value(
			"Item Price",
			{"item_code": item.item_code, "price_list": price_list, "selling": 1},
			["price_list_rate", "currency"],
			as_dict=True,
		)
		if price:
			item.price = fmt_money(price.price_list_rate, currency=price.currency)
	return items


def get_brands():
	return frappe.get_all("Brand", fields=["name", "image"], order_by="modified desc", limit=8)
