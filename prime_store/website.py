import frappe
from frappe import _
from frappe.query_builder.functions import Avg, Count
from frappe.utils import flt


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
		site_name=get_site_name(settings),
		address=frappe.db.get_single_value("Website Settings", "address"),
		trending=get_trending_menu(),
	)


TRENDING_KEY = "prime_store:trending_menu"
TRENDING_TTL = 300  # seconds; the menu is on every page, so don't rebuild it per request


def get_trending_menu():
	data = frappe.cache.get_value(TRENDING_KEY)
	if data is None:
		data = build_trending_menu()
		frappe.cache.set_value(TRENDING_KEY, data, expires_in_sec=TRENDING_TTL)
	return data


def build_trending_menu():
	"""Mega menu: categories as link columns of their top products, two as image tiles with a from-price."""
	from frappe.utils import fmt_money

	from prime_store.api import get_list_prices

	groups = [g for g in get_categories() if g.count]
	if not groups:
		return {}
	price_list = frappe.get_cached_doc("Webshop Settings").price_list
	currency = frappe.db.get_value("Price List", price_list, "currency") if price_list else None

	def top_items(group, limit):
		return frappe.get_all(
			"Website Item",
			filters={"published": 1, "item_group": group.name},
			fields=["item_code", "web_item_name", "route", "website_image"],
			order_by="ranking desc, creation desc",
			limit=limit,
		)

	columns = [
		{
			"name": g.item_group_name or g.name,
			"route": g.route,
			"items": [{"name": i.web_item_name, "route": i.route} for i in top_items(g, 7)],
		}
		for g in groups[:3]
	]

	tiles = []
	for g in (groups[3:] + groups[:3])[:2]:
		items = top_items(g, 20)
		prices = get_list_prices([i.item_code for i in items], price_list)
		image = g.image or next((i.website_image for i in items if i.website_image), None)
		tiles.append(
			{
				"name": g.item_group_name or g.name,
				"route": g.route,
				"image": image,
				"from_price": fmt_money(min(prices.values()), currency=currency) if prices else None,
			}
		)
	return {"columns": columns, "tiles": tiles}


def get_listing_facets(item_group=None):
	"""Counts and extras for the listing sidebar (brand logos, tags, ratings), scoped to the page's group."""
	try:
		return _listing_facets(item_group)
	except Exception:
		frappe.log_error(title="Prime Store: listing facets")
		return {"categories": [], "brands": {}, "tags": [], "ratings": []}


def _listing_facets(item_group):
	item = frappe.qb.DocType("Website Item")
	scope = item.published == 1
	if item_group:
		scope &= item.item_group == item_group

	brand_counts = dict(
		frappe.qb.from_(item).select(item.brand, Count(item.name))
		.where(scope & item.brand.isnotnull()).groupby(item.brand).run()
	)
	brand_images = dict(
		frappe.get_all("Brand", filters={"name": ["in", list(brand_counts) or [""]]}, fields=["name", "image"], as_list=True)
	)

	tag = frappe.qb.DocType("Tag Link")
	tags = (
		frappe.qb.from_(tag).join(item).on(tag.document_name == item.name)
		.select(tag.tag, Count(tag.name))
		.where((tag.document_type == "Website Item") & scope)
		.groupby(tag.tag).orderby(tag.tag).run()
	)

	ratings = []
	if frappe.get_cached_doc("Webshop Settings").enable_reviews:
		review = frappe.qb.DocType("Item Review")
		averages = [
			flt(avg) * 5
			for _name, avg in frappe.qb.from_(review).join(item).on(review.website_item == item.name)
			.select(review.website_item, Avg(review.rating)).where(scope).groupby(review.website_item).run()
		]
		ratings = [(stars, sum(1 for a in averages if a >= stars)) for stars in (4, 3, 2, 1)] if averages else []

	return {
		"categories": get_categories(limit=50),
		"brands": {name: {"count": n, "image": brand_images.get(name)} for name, n in brand_counts.items()},
		"tags": tags,
		"ratings": ratings,
	}


HOME_CACHE_PREFIX = "prime_store:home:"


def clear_trending_menu(doc=None, method=None):
	"""Drop cached storefront data (trending menu, guest homepage) after catalogue changes."""
	frappe.cache.delete_value(TRENDING_KEY)
	frappe.cache.delete_keys(HOME_CACHE_PREFIX)


def get_site_name(settings):
	# Website Settings ships with app_name "Frappe"; until the client sets their own, show the company.
	name = frappe.db.get_single_value("Website Settings", "app_name")
	return name if name and name != "Frappe" else settings.company


def get_categories(limit=12):
	# Leaf groups only: parents like the default "Products" just repeat their children.
	groups = frappe.get_all(
		"Item Group",
		filters={"show_in_website": 1, "is_group": 0},
		fields=["name", "item_group_name", "route", "image", "is_group", "parent_item_group"],
		order_by="lft asc",
		limit=limit,
	)
	counts = {}
	if groups:
		item = frappe.qb.DocType("Website Item")
		counts = dict(
			frappe.qb.from_(item)
			.select(item.item_group, Count(item.name))
			.where((item.published == 1) & item.item_group.isin([g.name for g in groups]))
			.groupby(item.item_group)
			.run()
		)
	for g in groups:
		g.count = counts.get(g.name, 0)
	return groups


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
