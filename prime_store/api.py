import json

import frappe
from frappe.query_builder.functions import Avg, Count
from frappe.utils import cint, flt
from webshop.webshop.doctype.override_doctype.item_group import get_child_groups_for_website
from webshop.webshop.product_data_engine.query import ProductQuery

SORTS = ("ranking", "newest", "price_asc", "price_desc", "name")
NO_LIMIT = 0


class PrimeProductQuery(ProductQuery):
	"""Webshop's ProductQuery plus sorting, a price range and an in-stock filter.

	Filtering, search, pricing rules, stock, cart and wishlist flags all stay Webshop's own;
	only the ordering and slicing of the matched Website Items happen here.
	"""

	def __init__(self, sort=None, price_min=None, price_max=None, in_stock=False, page_length=None):
		super().__init__()
		self.sort = sort if sort in SORTS else "ranking"
		self.price_min = flt(price_min) if price_min not in (None, "") else None
		self.price_max = flt(price_max) if price_max not in (None, "") else None
		self.in_stock = cint(in_stock) and self.settings.show_stock_availability
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
			self.filters.append(["item_code", "in", list(set.intersection(*item_codes)) or [""]])

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
		items = frappe.get_all(
			"Website Item",
			fields=[*self.fields, "brand"],
			filters={"name": ["in", names]},
			limit_page_length=NO_LIMIT,
		)
		order = {name: i for i, name in enumerate(names)}
		return sorted(items, key=lambda i: order[i.name])


def get_list_prices(item_codes, price_list):
	if not item_codes or not price_list:
		return {}
	prices = {}
	for row in frappe.get_all(
		"Item Price",
		filters={"item_code": ["in", item_codes], "price_list": price_list, "selling": 1},
		fields=["item_code", "price_list_rate", "customer"],
		limit_page_length=NO_LIMIT,
	):
		if row.customer:
			continue
		current = prices.get(row.item_code)
		prices[row.item_code] = row.price_list_rate if current is None else min(current, row.price_list_rate)
	return prices


def add_ratings(items, settings):
	"""Average review rating (out of 5) when Webshop reviews are switched on."""
	if not items or not settings.enable_reviews:
		return
	review = frappe.qb.DocType("Item Review")
	rows = (
		frappe.qb.from_(review)
		.select(review.website_item, Avg(review.rating), Count(review.name))
		.where(review.website_item.isin([i.name for i in items]))
		.groupby(review.website_item)
		.run()
	)
	by_item = {name: (rating, count) for name, rating, count in rows}
	for item in items:
		rating, count = by_item.get(item.name, (0, 0))
		if count:
			item.rating = round(flt(rating) * 5, 1)
			item.reviews = count


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

	engine = PrimeProductQuery(
		sort=args.sort, price_min=args.price_min, price_max=args.price_max, in_stock=args.in_stock
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
			{"name": g.name, "route": g.route}
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
