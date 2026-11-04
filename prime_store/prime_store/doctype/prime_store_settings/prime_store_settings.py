import frappe
from frappe.model.document import Document

SOCIAL_FIELDS = ("facebook", "instagram", "tiktok", "x", "youtube", "whatsapp")


class PrimeStoreSettings(Document):
	def on_update(self):
		# Header, footer and homepage are cached for guests; show the new settings straight away.
		from prime_store.website import clear_trending_menu

		clear_trending_menu()
		frappe.clear_cache()


def get_settings():
	"""Storefront settings from the desk, falling back to the older site_config keys (cached per request)."""
	cached = getattr(frappe.local, "prime_store_settings", None)
	if cached is None:
		cached = frappe.local.prime_store_settings = _load_settings()
	return cached


def _load_settings():
	doc = frappe.get_cached_doc("Prime Store Settings")
	conf = frappe.conf
	perks = [p.strip() for p in (doc.perks or "").splitlines() if p.strip()] or [
		p for p in (conf.get("prime_store_perks") or []) if p
	]
	social = [{"label": frappe.get_meta("Prime Store Settings").get_label(f), "url": doc.get(f)} for f in SOCIAL_FIELDS if doc.get(f)]
	if not social:
		social = [{"label": label, "url": url} for label, url in (conf.get("prime_store_social") or {}).items() if url]
	return frappe._dict(
		perks=perks,
		social=social,
		announcement=doc.announcement or conf.get("prime_store_announcement"),
		shop_url=doc.shop_url or conf.get("prime_store_shop_url") or "/all-products",
		hero_slideshow=doc.hero_slideshow or conf.get("prime_store_slideshow") or "Home Hero",
		offers_slideshow=doc.offers_slideshow or conf.get("prime_store_offers_slideshow") or "Home Offers",
		deal_end=str(doc.deal_end).replace(" ", "T") if doc.deal_end else conf.get("prime_store_deal_end"),
		swatch_attribute=doc.swatch_attribute or "Color",
		enable_compare=doc.enable_compare is None or bool(int(doc.enable_compare)),
	)
