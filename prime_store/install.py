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


def before_uninstall():
	if frappe.db.get_single_value("Website Settings", "home_page") == HOME:
		frappe.db.set_single_value("Website Settings", "home_page", "")
