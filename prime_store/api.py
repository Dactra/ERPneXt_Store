import json

import frappe
from frappe.query_builder.functions import Avg, Count
from frappe.utils import cint, flt
from webshop.webshop.doctype.override_doctype.item_group import get_child_groups_for_website
from webshop.webshop.product_data_engine.query import ProductQuery

from prime_store.prime_store.doctype.prime_store_settings.prime_store_settings import get_settings

SORTS = ("ranking", "newest", "price_asc", "price_desc", "name")
NO_LIMIT = 0


class PrimeProductQuery(ProductQuery):
	"""Webshop's ProductQuery plus sorting, a price range and an in-stock filter.

	Filtering, search, pricing rules, stock, cart and wishlist flags all stay Webshop's own;
	only the ordering and slicing of the matched Website Items happen here.
	"""

	def __init__(
		self, sort=None, price_min=None, price_max=None, in_stock=False, page_length=None, tags=None, rating_min=None
	):
		super().__init__()
		self.sort = sort if sort in SORTS else "ranking"
		self.price_min = flt(price_min) if price_min not in (None, "") else None
		self.price_max = flt(price_max) if price_max not in (None, "") else None
		self.in_stock = cint(in_stock) and self.settings.show_stock_availability
		self.tags = [t for t in (tags or []) if t]
		self.rating_min = flt(rating_min) if self.settings.enable_reviews else 0
		if page_length:
			self.page_length = cint(page_length)
		self.price_range = None

	def query(self, attributes=None, fields=None, search_term=None, start=0, item_group=None):
		fields = fields or {}
		if fields:
			self.build_fields_filters(fields)
		if item_group:
			self.build_item_group_filters(item_group)
		if search_term:
			self.build_search_filters(search_term)
		if self.settings.hide_variants:
			self.filters.append(["variant_of", "is", "not set"])
		if attributes:
			self.build_attribute_filters(attributes)

		rows = self.get_matching_rows()
		count = len(rows)
		page = rows[cint(start) : cint(start) + self.page_length]
		items = self.get_page_items([r.name for r in page])

		cart_items = self.get_cart_items() if self.settings.enabled else []
		items, _discounts = self.add_display_details(items, [], cart_items)
		add_template_prices(items, self.settings.price_list)
		add_color_swatches(items)
		add_ratings(items, self.settings)
		return {"items": items, "items_count": count}

	def build_attribute_filters(self, attributes):
		"""Same rule as ProductQuery.query_items_with_attributes: an item must match every attribute."""
		item_codes = []
		for attribute, values in attributes.items():
			values = values if isinstance(values, list) else [values]
			item_codes.append(
				set(
					frappe.get_all(
						"Item",
						filters=[
							["published_in_website", "=", 1],
							["Item Variant Attribute", "attribute", "=", attribute],
							["Item Variant Attribute", "attribute_value", "in", values],
						],
						pluck="item_code",
					)
				)
			)
		if item_codes:
			matched = set.intersection(*item_codes)
			if self.settings.hide_variants and matched:
				# Variants aren't listed, so a variant matching (say) Black + 256GB shows its template.
				matched |= set(
					frappe.get_all(
						"Item",
						filters={"item_code": ["in", list(matched)], "variant_of": ["is", "set"]},
						pluck="variant_of",
					)
				)
			self.filters.append(["item_code", "in", list(matched) or [""]])

	def get_matching_rows(self):
		rows = frappe.get_all(
			"Website Item",
			fields=["name", "item_code", "ranking", "creation", "web_item_name", "website_warehouse", "on_backorder"],
			filters=self.filters,
			or_filters=self.or_filters,
			limit_page_length=NO_LIMIT,
			order_by="ranking desc, creation desc",
		)
		# The Website Item Group join can repeat a row.
		seen, unique = set(), []
		for row in rows:
			if row.name not in seen:
				seen.add(row.name)
				unique.append(row)

		prices = get_list_prices([r.item_code for r in unique], self.settings.price_list)
		for row in unique:
			row.price = prices.get(row.item_code)

		known = [r.price for r in unique if r.price is not None]
		if known:
			self.price_range = [min(known), max(known)]

		# Price filter and sort use the price list rate; the card shows the final price after pricing rules.
		if self.price_min is not None:
			unique = [r for r in unique if r.price is not None and r.price >= self.price_min]
		if self.price_max is not None:
			unique = [r for r in unique if r.price is not None and r.price <= self.price_max]
		if self.in_stock:
			unique = [r for r in unique if self.row_in_stock(r)]
		if self.tags:
			# Any of the selected tags (Frappe's own document tags on Website Item).
			tagged = set(
				frappe.get_all(
					"Tag Link",
					filters={"document_type": "Website Item", "tag": ["in", self.tags]},
					pluck="document_name",
				)
			)
			unique = [r for r in unique if r.name in tagged]
		if self.rating_min:
			ratings = get_average_ratings([r.name for r in unique])
			unique = [r for r in unique if ratings.get(r.name, 0) >= self.rating_min]

		if self.sort == "newest":
			unique.sort(key=lambda r: r.creation, reverse=True)
		elif self.sort == "name":
			unique.sort(key=lambda r: (r.web_item_name or "").lower())
		elif self.sort in ("price_asc", "price_desc"):
			high = self.sort == "price_desc"
			priced = sorted((r for r in unique if r.price is not None), key=lambda r: r.price, reverse=high)
			unique = priced + [r for r in unique if r.price is None]
		return unique

	def row_in_stock(self, row):
		self.get_stock_availability(row)
		return bool(row.in_stock or row.on_backorder)

	def get_page_items(self, names):
		if not names:
			return []
		fields = [*self.fields, "brand"]
		# Added by after_migrate; skip it until the first migrate has run.
		if frappe.get_meta("Website Item").has_field("prime_store_badge"):
			fields.append("prime_store_badge")
		items = frappe.get_all(
			"Website Item",
			fields=fields,
			filters={"name": ["in", names]},
			limit_page_length=NO_LIMIT,
		)
		order = {name: i for i, name in enumerate(names)}
		return sorted(items, key=lambda i: order[i.name])


def get_list_prices(item_codes, price_list):
	"""{item_code: lowest list rate}; a template (no Item Price allowed in v16) gets its cheapest variant's."""
	if not item_codes or not price_list:
		return {}
	prices = _lowest_rates(item_codes, price_list)
	missing = [code for code in item_codes if code not in prices]
	if missing:
		variants = frappe.get_all(
			"Item", filters={"variant_of": ["in", missing], "disabled": 0}, fields=["name", "variant_of"],
			limit_page_length=NO_LIMIT,
		)
		variant_prices = _lowest_rates([v.name for v in variants], price_list)
		for v in variants:
			rate = variant_prices.get(v.name)
			if rate is not None:
				prices[v.variant_of] = rate if v.variant_of not in prices else min(prices[v.variant_of], rate)
	return prices


def _lowest_rates(item_codes, price_list):
	prices = {}
	if not item_codes:
		return prices
	for row in frappe.get_all(
		"Item Price",
		filters={"item_code": ["in", item_codes], "price_list": price_list, "selling": 1},
		fields=["item_code", "price_list_rate", "customer"],
		limit_page_length=NO_LIMIT,
	):
		if row.customer or row.price_list_rate <= 0:  # a zero rate means "not priced yet"
			continue
		current = prices.get(row.item_code)
		prices[row.item_code] = row.price_list_rate if current is None else min(current, row.price_list_rate)
	return prices


def add_template_prices(items, price_list):
	"""Cards for templates show "starting at" their cheapest variant (Webshop gives templates no price)."""
	templates = [i for i in items if i.has_variants and not i.formatted_price]
	if not templates:
		return
	from frappe.utils import fmt_money

	currency = frappe.db.get_value("Price List", price_list, "currency") if price_list else None
	prices = get_list_prices([i.item_code for i in templates], price_list)
	for item in templates:
		if item.item_code in prices:
			item.formatted_price = fmt_money(prices[item.item_code], currency=currency)


COMPARE_MAX = 4


def get_compare_items(item_codes):
	"""Products for the compare page, priced and stocked like the cards, plus their attribute values.

	Returns (items, attributes): attributes is the ordered list of attribute names; each item gets
	`specs` = {attribute: "value, value"} (a template lists what its variants offer).
	"""
	codes = list(dict.fromkeys(c for c in item_codes if c))[:COMPARE_MAX]
	if not codes:
		return [], []
	engine = PrimeProductQuery()
	rows = frappe.get_all(
		"Website Item", filters={"item_code": ["in", codes], "published": 1}, fields=["name", "item_code"]
	)
	order = {code: i for i, code in enumerate(codes)}
	names = [r.name for r in sorted(rows, key=lambda r: order[r.item_code])]
	items = engine.get_page_items(names)
	cart_items = engine.get_cart_items() if engine.settings.enabled else []
	items, _discounts = engine.add_display_details(items, [], cart_items)
	add_template_prices(items, engine.settings.price_list)
	add_ratings(items, engine.settings)

	shown = [i.item_code for i in items]
	attr = frappe.qb.DocType("Item Variant Attribute")
	variant = frappe.qb.DocType("Item")
	attr_rows = (
		frappe.qb.from_(attr)
		.join(variant).on(attr.parent == variant.name)
		.select(variant.name, variant.variant_of, attr.attribute, attr.attribute_value)
		.where(
			(variant.name.isin(shown) | variant.variant_of.isin(shown))
			& (variant.disabled == 0) & attr.attribute_value.isnotnull()
		)
		.orderby(attr.idx).orderby(variant.name)
		.run()
	) if shown else []
	attributes, specs = [], {code: {} for code in shown}
	for name, variant_of, attribute, value in attr_rows:
		for owner in {name, variant_of} & set(shown):
			values = specs[owner].setdefault(attribute, [])
			if value not in values:
				values.append(value)
		if attribute not in attributes:
			attributes.append(attribute)
	for item in items:
		item.specs = specs.get(item.item_code, {})
	return items, attributes


def add_color_swatches(items, limit=5):
	"""Templates get their variants' colours (with each colour's image) for the card swatches."""
	templates = {i.item_code: i for i in items if i.has_variants}
	if not templates:
		return
	attr = frappe.qb.DocType("Item Variant Attribute")
	variant = frappe.qb.DocType("Item")
	web = frappe.qb.DocType("Website Item")
	rows = (
		frappe.qb.from_(attr)
		.join(variant).on(attr.parent == variant.name)
		.left_join(web).on(web.item_code == variant.name)
		.select(variant.variant_of, attr.attribute_value, web.website_image, variant.image)
		.where(
			variant.variant_of.isin(list(templates)) & (variant.disabled == 0)
			& (attr.attribute == get_settings().swatch_attribute) & attr.attribute_value.isnotnull()
		)
		.orderby(variant.variant_of).orderby(variant.name)
		.run()
	)
	for template, value, web_image, image in rows:
		item = templates[template]
		swatches = item.setdefault("swatches", [])
		if any(s["value"] == value for s in swatches):
			continue
		image = web_image or image
		# Only a picture that differs from the card's is worth swapping to.
		swatches.append({"value": value, "image": image if image and image != item.website_image else None})
	for item in templates.values():
		if item.get("swatches"):
			item.swatches_more = max(0, len(item.swatches) - limit)
			item.swatches = item.swatches[:limit]


def add_ratings(items, settings):
	"""Average review rating (out of 5) when Webshop reviews are switched on."""
	if not items or not settings.enable_reviews:
		return
	by_item = get_review_stats([i.name for i in items])
	for item in items:
		rating, count = by_item.get(item.name, (0, 0))
		if count:
			item.rating = round(flt(rating) * 5, 1)
			item.reviews = count


def get_review_stats(names):
	"""{website_item: (average rating 0-1, review count)}"""
	if not names:
		return {}
	review = frappe.qb.DocType("Item Review")
	rows = (
		frappe.qb.from_(review)
		.select(review.website_item, Avg(review.rating), Count(review.name))
		.where(review.website_item.isin(names))
		.groupby(review.website_item)
		.run()
	)
	return {name: (rating, count) for name, rating, count in rows}


def get_average_ratings(names):
	"""{website_item: average rating out of 5}"""
	return {name: flt(rating) * 5 for name, (rating, _count) in get_review_stats(names).items()}


@frappe.whitelist(allow_guest=True)
def get_product_filter_data(query_args=None):
	"""Listing data for /all-products and item group pages, with the cards already rendered."""
	from prime_store.website import render_product_cards

	if isinstance(query_args, str):
		query_args = json.loads(query_args)
	args = frappe._dict(query_args or {})

	field_filters = args.field_filters or {}
	attribute_filters = args.attribute_filters or {}
	if isinstance(field_filters, str):
		field_filters = json.loads(field_filters)
	if isinstance(attribute_filters, str):
		attribute_filters = json.loads(attribute_filters)

	tags = args.tags or []
	if isinstance(tags, str):
		tags = json.loads(tags) if tags.startswith("[") else tags.split(",")
	engine = PrimeProductQuery(
		sort=args.sort,
		price_min=args.price_min,
		price_max=args.price_max,
		in_stock=args.in_stock,
		tags=tags,
		rating_min=args.rating_min,
	)
	start = max(cint(args.start), 0)
	try:
		result = engine.query(
			attribute_filters,
			field_filters,
			search_term=(args.search or "").strip() or None,
			start=start,
			item_group=args.item_group,
		)
	except Exception:
		frappe.log_error(title="Prime Store: product listing")
		return {"exc": "query_failed"}

	sub_categories = []
	if args.item_group:
		sub_categories = [
			{"name": g.name, "label": frappe._(g.name), "route": g.route}
			for g in get_child_groups_for_website(args.item_group, immediate=True)
		]

	return {
		"html": render_product_cards(result["items"], engine.settings),
		"items_count": result["items_count"],
		"start": start,
		"page_length": engine.page_length,
		"price_range": engine.price_range,
		"sub_categories": sub_categories,
	}
