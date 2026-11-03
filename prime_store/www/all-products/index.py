import frappe
from webshop.webshop.product_data_engine.filters import ProductFiltersBuilder

# Replaces Webshop's /all-products page (prime_store is installed after webshop, so its www wins).
sitemap = 1


def get_context(context):
	context.body_class = "product-page"
	context.parents = [{"name": frappe._("Home"), "route": "/"}]
	context.no_cache = 1

	filter_engine = ProductFiltersBuilder()
	context.field_filters = filter_engine.get_field_filters()
	context.attribute_filters = filter_engine.get_attribute_filters()
	context.settings = frappe.get_cached_doc("Webshop Settings")
