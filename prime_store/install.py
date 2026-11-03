import frappe

HOME = "store-home"


def after_install():
	"""Point the site home page at the storefront only if the client hasn't chosen one."""
	if not frappe.db.get_single_value("Website Settings", "home_page"):
		frappe.db.set_single_value("Website Settings", "home_page", HOME)


def before_uninstall():
	if frappe.db.get_single_value("Website Settings", "home_page") == HOME:
		frappe.db.set_single_value("Website Settings", "home_page", "")
