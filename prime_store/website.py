import frappe
from frappe import _
from frappe.query_builder.functions import Avg, Count
from frappe.utils import flt

from prime_store.prime_store.doctype.prime_store_settings.prime_store_settings import get_settings


def get_prime_store_settings():
	"""Jinja helper: the storefront settings (Prime Store Settings)."""
	return get_settings()


def update_website_context(context):
	"""Header/footer data for every web page. Must never break a page, so failures only log."""
	try:
		context.ps = get_store_context()
	except Exception:
		frappe.log_error(title="Prime Store: website context")
		context.ps = frappe._dict(categories=[], category_tree=[], perks=[], social=[], compare_enabled=False)


def get_store_context():
	settings = frappe.get_cached_doc("Webshop Settings")
	contact = frappe.get_cached_doc("Contact Us Settings")
	store = get_settings()
	tree = get_category_tree()
	return frappe._dict(
		# Top-level categories (a parent such as "Smart Home" counts its sub-categories' products).
		categories=tree,
		category_tree=tree,
		signup_enabled=not frappe.db.get_single_value("Website Settings", "disable_signup"),
		# Feature strip and social links are per-client facts (Prime Store Settings); hidden when empty.
		perks=store.perks,
		social=store.social,
		compare_enabled=store.enable_compare,
		cart_enabled=settings.enabled,
		checkout_enabled=settings.enable_checkout,
		wishlist_enabled=settings.enabled and settings.enable_wishlist,
		email=contact.email_id,
		phone=contact.phone,
		shop_url=store.shop_url,
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
		return {"categories": [], "brands": {}, "tags": [], "ratings": [], "attributes": {}}


def _listing_facets(item_group):
	item = frappe.qb.DocType("Website Item")
	scope = item.published == 1
	if item_group:
		scope &= item.item_group.isin(get_descendant_groups(item_group))

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

	# Products per attribute value (Color, Storage...): a template counts once however many variants match.
	variant = frappe.qb.DocType("Item")
	attr = frappe.qb.DocType("Item Variant Attribute")
	product = item.item_code if not frappe.get_cached_doc("Webshop Settings").hide_variants else variant.variant_of
	rows = (
		frappe.qb.from_(attr)
		.join(variant).on(attr.parent == variant.name)
		.join(item).on(item.item_code == product)
		.select(attr.attribute, attr.attribute_value, Count(item.name).distinct())
		.where(scope & attr.attribute_value.isnotnull() & (variant.published_in_website == 1))
		.groupby(attr.attribute, attr.attribute_value)
		.run()
	)
	attributes = {}
	for attribute, value, n in rows:
		attributes.setdefault(attribute, {})[value] = n

	return {
		"categories": get_category_tree(),
		# The open branch of the category tree: the current group and its parents.
		"category_path": get_group_path(item_group),
		"brands": {name: {"count": n, "image": brand_images.get(name)} for name, n in brand_counts.items()},
		"tags": tags,
		"ratings": ratings,
		"attributes": attributes,
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
	counts = get_group_counts([g.name for g in groups])
	for g in groups:
		g.count = counts.get(g.name, 0)
	return groups


def get_group_counts(group_names):
	"""{item_group: listed products}; hidden variants don't count as separate products."""
	if not group_names:
		return {}
	item = frappe.qb.DocType("Website Item")
	condition = (item.published == 1) & item.item_group.isin(group_names)
	if frappe.get_cached_doc("Webshop Settings").hide_variants:
		condition &= item.variant_of.isnull() | (item.variant_of == "")
	return dict(
		frappe.qb.from_(item).select(item.item_group, Count(item.name)).where(condition).groupby(item.item_group).run()
	)


def get_descendant_groups(item_group):
	"""The group and every group under it (for counts that include sub-categories)."""
	bounds = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
	if not bounds:
		return [item_group]
	return frappe.get_all(
		"Item Group", filters={"lft": [">=", bounds.lft], "rgt": ["<=", bounds.rgt]}, pluck="name"
	)


def get_group_path(item_group):
	path = []
	while item_group and item_group not in path:
		path.append(item_group)
		item_group = frappe.db.get_value("Item Group", item_group, "parent_item_group")
	return path


def get_category_tree():
	"""Website item groups as a tree for the mobile menu; a parent counts its children's products."""
	groups = frappe.get_all(
		"Item Group",
		filters={"show_in_website": 1},
		fields=["name", "item_group_name", "route", "image", "parent_item_group", "lft"],
		order_by="lft asc",
	)
	by_name = {g.name: g for g in groups}
	counts = get_group_counts(list(by_name))
	for g in groups:
		g.count = counts.get(g.name, 0)
		g.children = []
	top = []
	for g in groups:
		parent = by_name.get(g.parent_item_group)
		(parent.children if parent else top).append(g)

	def total(node):
		node.count += sum(total(child) for child in node.children)
		return node.count

	def prune(nodes):
		kept = [n for n in nodes if n.count]
		for n in kept:
			n.children = prune(n.children)
		return kept

	for node in top:
		total(node)
	return prune(top)


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


def get_starting_price(item_code):
	"""Jinja helper: a template's cheapest variant price, formatted (templates have no Item Price)."""
	from frappe.utils import fmt_money

	from prime_store.api import get_list_prices

	price_list = frappe.get_cached_doc("Webshop Settings").price_list
	rate = get_list_prices([item_code], price_list).get(item_code)
	if rate is None:
		return None
	return fmt_money(rate, currency=frappe.db.get_value("Price List", price_list, "currency"))


def get_webshop_settings():
	return frappe.get_cached_doc("Webshop Settings")


def render_product_cards(items, settings=None):
	settings = settings or get_webshop_settings()
	return frappe.render_template(
		"templates/includes/prime_store/product_cards.html", {"items": items, "settings": settings, "_": _}
	)
