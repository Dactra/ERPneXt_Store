import frappe
from frappe import _


def update_website_context(context):
	"""Header/footer data for every web page. Must never break a page, so failures only log."""
	try:
		context.ps = get_store_context()
	except Exception:
		frappe.log_error(title="Prime Store: website context")
		context.ps = frappe._dict(categories=[], perks=[], social=[])


def get_store_context():
	settings = frappe.get_cached_doc("Webshop Settings")
	contact = frappe.get_cached_doc("Contact Us Settings")
	return frappe._dict(
		categories=get_categories(),
		# Feature strip and social links are per-client facts, so they only show when configured.
		perks=[p for p in (frappe.conf.get("prime_store_perks") or []) if p],
		social=[
			{"label": label, "url": url}
			for label, url in (frappe.conf.get("prime_store_social") or {}).items()
			if url
		],
		cart_enabled=settings.enabled,
		checkout_enabled=settings.enable_checkout,
		wishlist_enabled=settings.enabled and settings.enable_wishlist,
		email=contact.email_id,
		phone=contact.phone,
		shop_url=frappe.conf.get("prime_store_shop_url") or "/all-products",
		site_name=frappe.db.get_single_value("Website Settings", "app_name")
		or frappe.db.get_single_value("System Settings", "app_name")
		or settings.company,
		address=frappe.db.get_single_value("Website Settings", "address"),
	)


def get_categories(limit=12):
	return frappe.get_all(
		"Item Group",
		filters={"show_in_website": 1},
		fields=["name", "item_group_name", "route", "image", "is_group", "parent_item_group"],
		order_by="lft asc",
		limit=limit,
	)


def get_products(item_group=None, exclude=None, limit=8, sort=None):
	"""Product cards priced and stocked by Webshop's own engine (pricing rules, stock, cart, wishlist)."""
	from prime_store.api import PrimeProductQuery

	engine = PrimeProductQuery(sort=sort, page_length=limit + (1 if exclude else 0))
	items = engine.query(item_group=item_group)["items"]
	return [i for i in items if i.item_code != exclude][:limit]


def get_related_products(doc, limit=4):
	"""Jinja helper for the product page: other items from the same group."""
	if not doc.item_group:
		return []
	try:
		return get_products(item_group=doc.item_group, exclude=doc.item_code, limit=limit)
	except Exception:
		frappe.log_error(title="Prime Store: related products")
		return []


def get_webshop_settings():
	return frappe.get_cached_doc("Webshop Settings")


def render_product_cards(items, settings=None):
	settings = settings or get_webshop_settings()
	return frappe.render_template(
		"templates/includes/prime_store/product_cards.html", {"items": items, "settings": settings, "_": _}
	)
