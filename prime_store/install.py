import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

HOME = "store-home"

# Shown as the coloured label on product cards; picked per Website Item in the desk.
BADGES = ("New Arrival", "Trending", "Exclusive", "Best Seller", "Sale")
CUSTOM_FIELDS = {
	"Website Item": [
		{
			"fieldname": "prime_store_badge",
			"label": "Store Badge",
			"fieldtype": "Select",
			"options": "\n" + "\n".join(BADGES),
			"insert_after": "brand",
			"description": "Label shown on the product card in the storefront.",
		}
	]
}


def after_install():
	"""Point the site home page at the storefront only if the client hasn't chosen one."""
	if not frappe.db.get_single_value("Website Settings", "home_page"):
		frappe.db.set_single_value("Website Settings", "home_page", HOME)
	after_migrate()


def after_migrate():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	seed_settings()


# site_config keys used before Prime Store Settings existed; copied once so upgrades keep their content.
LEGACY_KEYS = {
	"prime_store_announcement": "announcement",
	"prime_store_shop_url": "shop_url",
	"prime_store_slideshow": "hero_slideshow",
	"prime_store_offers_slideshow": "offers_slideshow",
}


def seed_settings():
	"""First run: save Prime Store Settings with its defaults plus any legacy site_config values."""
	if frappe.db.sql("select 1 from `tabSingles` where doctype = %s limit 1", "Prime Store Settings"):
		return
	doc = frappe.get_single("Prime Store Settings")
	doc.shop_url = doc.shop_url or "/all-products"
	doc.enable_compare = 1
	if frappe.db.exists("Item Attribute", "Color"):
		doc.swatch_attribute = "Color"
	conf = frappe.conf
	for key, field in LEGACY_KEYS.items():
		if conf.get(key) and (field not in ("hero_slideshow", "offers_slideshow") or frappe.db.exists("Website Slideshow", conf.get(key))):
			doc.set(field, conf.get(key))
	doc.perks = "\n".join(p for p in (conf.get("prime_store_perks") or []) if p)
	social = conf.get("prime_store_social") or {}
	for field in ("facebook", "instagram", "tiktok", "x", "youtube", "whatsapp"):
		if social.get(field):
			doc.set(field, social[field])
	if conf.get("prime_store_deal_end"):
		doc.deal_end = conf.get("prime_store_deal_end").replace("T", " ")
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.save()


def before_uninstall():
	if frappe.db.get_single_value("Website Settings", "home_page") == HOME:
		frappe.db.set_single_value("Website Settings", "home_page", "")
