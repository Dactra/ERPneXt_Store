app_name = "prime_store"
app_title = "Prime Store"
app_publisher = "Your Company"
app_description = "Electronics storefront theme for ERPNext Webshop"
app_email = "you@example.com"
app_license = "mit"

# Webshop is a separate app ("webshop") on v16.
required_apps = ["erpnext", "webshop"]

web_include_css = ["/assets/prime_store/css/prime_store.css"]
web_include_js = ["/assets/prime_store/js/prime_store.js"]

after_install = "prime_store.install.after_install"
before_uninstall = "prime_store.install.before_uninstall"
