app_name = "prime_store"
app_title = "Prime Store"
app_publisher = "Your Company"
app_description = "Electronics storefront theme for ERPNext Webshop"
app_email = "you@example.com"
app_license = "mit"

# Webshop is a separate app ("webshop") on v16. Install prime_store after it: its templates and
# www pages (header, footer, listing, product page) take precedence over Webshop's.
required_apps = ["erpnext", "webshop"]

from prime_store import __version__

# Plain (unhashed) files: the version query makes CDNs such as Cloudflare fetch each release fresh.
web_include_css = [f"/assets/prime_store/css/prime_store.css?v={__version__}"]
web_include_js = [f"/assets/prime_store/js/prime_store.js?v={__version__}"]

update_website_context = ["prime_store.website.update_website_context"]

jinja = {
	"methods": [
		"prime_store.website.get_related_products",
		"prime_store.website.get_listing_facets",
	]
}

# The trending menu and the guest homepage are cached; rebuild them when their source data changes.
_clear_menu = "prime_store.website.clear_trending_menu"
doc_events = {
	doctype: {"on_update": _clear_menu, "on_trash": _clear_menu}
	for doctype in ("Website Item", "Item Group", "Item Price", "Pricing Rule", "Brand", "Webshop Settings")
}

after_install = "prime_store.install.after_install"
after_migrate = "prime_store.install.after_migrate"
before_uninstall = "prime_store.install.before_uninstall"
