app_name = "prime_store"
app_title = "Prime Store"
app_publisher = "Dactra"
app_description = "Electronics storefront theme for ERPNext Webshop"
app_email = "you@example.com"
app_license = "mit"

# Webshop is a separate app ("webshop") on v16. Install prime_store after it: its templates and
# www pages (header, footer, listing, product page) take precedence over Webshop's.
required_apps = ["erpnext", "webshop"]

import hashlib
import os

from prime_store import __version__


def _asset(path):
	# Plain (unhashed) files: a content hash in the URL makes CDNs such as Cloudflare
	# fetch every change fresh, including hot fixes that keep the same app version.
	try:
		with open(os.path.join(os.path.dirname(__file__), "public", path), "rb") as f:
			version = hashlib.md5(f.read()).hexdigest()[:10]
	except OSError:
		version = __version__
	return f"/assets/prime_store/{path}?v={version}"


web_include_css = [_asset("css/prime_store.css")]
web_include_js = [_asset("js/prime_store.js")]

update_website_context = ["prime_store.website.update_website_context"]

jinja = {
	"methods": [
		"prime_store.website.get_related_products",
		"prime_store.website.get_listing_facets",
		"prime_store.website.get_starting_price",
		"prime_store.website.get_prime_store_settings",
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
