// Prime Store storefront behaviour. Cart and wishlist writes go through Webshop's own JS
// (webshop.webshop.shopping_cart / wishlist), so its rules and guest redirects still apply.
(function () {
	"use strict";

	var T = {};

	function ready(fn) {
		if (document.readyState !== "loading") fn();
		else document.addEventListener("DOMContentLoaded", fn);
	}

	function $all(sel, root) {
		return Array.prototype.slice.call((root || document).querySelectorAll(sel));
	}

	function alert(message, ok) {
		if (window.frappe && frappe.show_alert) {
			frappe.show_alert({ message: message, indicator: ok === false ? "red" : "green" }, 4);
		}
	}

	function cart() {
		return window.webshop && webshop.webshop && webshop.webshop.shopping_cart;
	}

	function wishlist() {
		return window.webshop && webshop.webshop && webshop.webshop.wishlist;
	}

	function isGuest() {
		return !window.frappe || !frappe.session || frappe.session.user === "Guest";
	}

	function toLogin() {
		try {
			localStorage.setItem("last_visited", location.pathname + location.search);
		} catch (e) {
			/* storage blocked: the login page still works */
		}
		location.href = "/login?redirect-to=" + encodeURIComponent(location.pathname + location.search);
	}

	/* ---------- header: counts, drawers, category menu ---------- */

	function getCookie(name) {
		var m = document.cookie.match("(?:^|; )" + name + "=([^;]*)");
		return m ? decodeURIComponent(m[1]) : "";
	}

	function updateCounts() {
		var counts = {
			cart: isGuest() ? 0 : parseInt(getCookie("cart_count"), 10) || 0,
			wish: isGuest() ? 0 : parseInt(getCookie("wish_count"), 10) || 0,
		};
		$all("[data-ps-count]").forEach(function (el) {
			var n = counts[el.dataset.psCount] || 0;
			el.textContent = n > 99 ? "99+" : String(n);
			el.hidden = n === 0;
		});
	}

	// Webshop refreshes its own (hidden) badges after cart/wishlist changes; refresh ours too.
	function hookWebshopCounts() {
		[
			[cart(), "set_cart_count"],
			[wishlist(), "set_wishlist_count"],
		].forEach(function (pair) {
			var obj = pair[0], name = pair[1];
			if (!obj || typeof obj[name] !== "function" || obj[name]._ps) return;
			var original = obj[name];
			obj[name] = function () {
				var out = original.apply(this, arguments);
				updateCounts();
				return out;
			};
			obj[name]._ps = true;
		});
	}

	var openDrawer = null, lastFocus = null;

	function setDrawer(drawer, open) {
		if (!drawer) return;
		drawer.classList.toggle("is-open", open);
		document.body.classList.toggle("ps-locked", open);
		$all('[data-ps-drawer="' + drawer.id + '"]').forEach(function (b) {
			b.setAttribute("aria-expanded", open ? "true" : "false");
		});
		if (open) {
			openDrawer = drawer;
			lastFocus = document.activeElement;
			var panel = drawer.querySelector(".ps-drawer__panel");
			if (panel) panel.focus();
		} else {
			openDrawer = null;
			if (lastFocus && lastFocus.focus) lastFocus.focus();
		}
	}

	function initDrawers() {
		document.addEventListener("click", function (e) {
			var opener = e.target.closest("[data-ps-drawer]");
			if (opener) {
				setDrawer(document.getElementById(opener.dataset.psDrawer), true);
				return;
			}
			if (openDrawer && e.target.closest("[data-ps-close]")) setDrawer(openDrawer, false);
		});
		document.addEventListener("keydown", function (e) {
			if (e.key === "Escape" && openDrawer) setDrawer(openDrawer, false);
		});
		// Closing the filter drawer must not leave the page locked when resized to desktop.
		window.addEventListener("resize", function () {
			if (openDrawer && getComputedStyle(openDrawer.querySelector(".ps-drawer__panel")).position !== "fixed") {
				setDrawer(openDrawer, false);
			}
		});
	}

	function initCategoryMenu(root) {
		var btn = root.querySelector("button");
		var list = root.querySelector("ul");
		function set(open) {
			list.hidden = !open;
			btn.setAttribute("aria-expanded", open ? "true" : "false");
		}
		btn.addEventListener("click", function () { set(list.hidden); });
		document.addEventListener("click", function (e) {
			if (!root.contains(e.target)) set(false);
		});
		root.addEventListener("keydown", function (e) {
			if (e.key === "Escape" && !list.hidden) {
				set(false);
				btn.focus();
			}
		});
	}

	/* ---------- cart and wishlist actions ---------- */

	function addToCart(btn, qty, done) {
		var sc = cart();
		if (!sc) return;
		if (isGuest()) return toLogin();
		btn.disabled = true;
		var call = sc.update_cart({
			item_code: btn.dataset.psAdd || btn.dataset.psBuyNow,
			qty: qty,
			callback: function (r) {
				btn.disabled = false;
				if (r && !r.exc) {
					alert(btn.dataset.psAdded || T.added_cart);
					if (done) done();
				}
			},
		});
		if (call && call.fail) {
			call.fail(function () {
				btn.disabled = false;
				alert(T.error, false);
			});
		}
	}

	function cardAdded(btn) {
		var link = document.createElement("a");
		link.className = "ps-btn ps-btn--ghost ps-btn--block";
		link.href = "/cart";
		link.innerHTML = '<svg class="ps-i ps-i--check" aria-hidden="true"><use href="#ps-i-check"></use></svg>';
		link.appendChild(document.createTextNode(btn.dataset.psAdded || ""));
		btn.replaceWith(link);
	}

	function toggleWish(btn) {
		var wl = wishlist();
		if (!wl) return;
		if (isGuest()) return toLogin();
		var adding = !btn.classList.contains("is-active");
		function set(on) {
			btn.classList.toggle("is-active", on);
			btn.setAttribute("aria-pressed", on ? "true" : "false");
		}
		set(adding);
		btn.disabled = true;
		wl.add_remove_from_wishlist(
			adding ? "add" : "remove",
			{ item_code: btn.dataset.psWish },
			function () {
				btn.disabled = false;
				wl.set_wishlist_count(true);
				alert(adding ? T.wish_added : T.wish_removed);
			},
			function () {
				btn.disabled = false;
				set(!adding);
				alert(T.error, false);
			}
		);
	}

	function initActions() {
		document.addEventListener("click", function (e) {
			var add = e.target.closest("[data-ps-add]");
			if (add && !add.closest("[data-ps-buy]")) {
				addToCart(add, 1, function () { cardAdded(add); });
				return;
			}
			var wish = e.target.closest("[data-ps-wish]");
			if (wish) {
				toggleWish(wish);
				return;
			}
			var step = e.target.closest("[data-ps-step]");
			if (step) {
				var input = step.parentNode.querySelector("input");
				input.value = Math.max(1, (parseInt(input.value, 10) || 1) + parseInt(step.dataset.psStep, 10));
				return;
			}
			var now = e.target.closest("[data-ps-buy-now]");
			if (now) {
				addToCart(now, qtyOf(now.closest("form")), function () { location.href = "/cart"; });
			}
		});

		$all("[data-ps-buy]").forEach(function (form) {
			form.addEventListener("submit", function (e) {
				e.preventDefault();
				var btn = form.querySelector("[data-ps-add]");
				addToCart(btn, qtyOf(form), function () {
					var view = document.querySelector("[data-ps-view-cart]");
					if (view) view.hidden = false;
				});
			});
		});
	}

	function qtyOf(form) {
		var input = form && form.querySelector('input[name="qty"]');
		var qty = input ? parseInt(input.value, 10) : 1;
		if (!qty || qty < 1) qty = 1;
		if (input) input.value = qty;
		return qty;
	}

	/* ---------- homepage ---------- */

	function initSlider(root) {
		var slides = $all(".ps-slide", root);
		var dots = $all("[data-ps-dot]", root);
		if (slides.length < 2) return;
		var index = 0, timer = null;
		var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

		function show(i) {
			index = (i + slides.length) % slides.length;
			slides.forEach(function (s, n) {
				var on = n === index;
				s.classList.toggle("is-active", on);
				s.setAttribute("aria-hidden", on ? "false" : "true");
				$all("a", s).forEach(function (a) { a.tabIndex = on ? 0 : -1; });
			});
			dots.forEach(function (d, n) {
				d.classList.toggle("is-active", n === index);
				if (n === index) d.setAttribute("aria-current", "true");
				else d.removeAttribute("aria-current");
			});
		}
		function start() { if (!reduce) timer = setInterval(function () { show(index + 1); }, 6000); }
		function stop() { clearInterval(timer); }

		root.querySelector("[data-ps-next]").addEventListener("click", function () { show(index + 1); });
		root.querySelector("[data-ps-prev]").addEventListener("click", function () { show(index - 1); });
		dots.forEach(function (d) {
			d.addEventListener("click", function () { show(parseInt(d.dataset.psDot, 10)); });
		});
		root.addEventListener("mouseenter", stop);
		root.addEventListener("mouseleave", start);
		root.addEventListener("focusin", stop);
		start();
	}

	function initCountdown(root) {
		var end = new Date(root.dataset.psCountdown).getTime();
		var clock = root.querySelector("[data-ps-clock]");
		if (isNaN(end) || !clock) return;

		function cell(value, label) {
			return "<div><b>" + String(value).padStart(2, "0") + "</b><span>" + label + "</span></div>";
		}
		function tick() {
			var left = Math.max(0, Math.floor((end - Date.now()) / 1000));
			if (left === 0) {
				clock.textContent = root.dataset.ended;
				clearInterval(timer);
				return;
			}
			clock.innerHTML =
				cell(Math.floor(left / 86400), root.dataset.d) +
				cell(Math.floor((left % 86400) / 3600), root.dataset.h) +
				cell(Math.floor((left % 3600) / 60), root.dataset.m) +
				cell(left % 60, root.dataset.s);
		}
		var timer = setInterval(tick, 1000);
		tick();
	}

	/* ---------- product page gallery ---------- */

	function initGallery(root) {
		var track = root.querySelector(".ps-gallery__track");
		var thumbs = $all("[data-ps-thumb]", root);
		if (!track || !thumbs.length) return;
		var slides = $all(".ps-gallery__slide", track);

		function mark(i) {
			thumbs.forEach(function (t, n) {
				if (n === i) t.setAttribute("aria-current", "true");
				else t.removeAttribute("aria-current");
			});
		}
		thumbs.forEach(function (t) {
			t.addEventListener("click", function () {
				var i = parseInt(t.dataset.psThumb, 10);
				slides[i].scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
				mark(i);
			});
		});
		var pending = null;
		track.addEventListener("scroll", function () {
			clearTimeout(pending);
			pending = setTimeout(function () {
				var i = Math.round(Math.abs(track.scrollLeft) / track.clientWidth);
				mark(Math.min(i, slides.length - 1));
			}, 80);
		});
	}

	/* ---------- product listing (/all-products and item group pages) ---------- */

	function Listing(root) {
		this.root = root;
		this.results = root.querySelector("[data-ps-results]");
		this.skeleton = this.results.innerHTML;
		this.form = root.querySelector("[data-ps-filter-form]");
		this.sort = root.querySelector("[data-ps-sort]");
		this.pager = root.querySelector("[data-ps-pager]");
		this.total = root.querySelector("[data-ps-total]");
		this.empty = root.querySelector("[data-ps-empty]");
		this.error = root.querySelector("[data-ps-error]");
		this.active = root.querySelector("[data-ps-active]");
		this.subcats = root.querySelector("[data-ps-subcats]");
		this.itemGroup = root.dataset.itemGroup || null;
		this.request = 0;

		this.readUrl();
		this.syncInputs();
		this.bind();
		this.setView(this.storedView());
		this.load();
	}

	Listing.prototype.readUrl = function () {
		var p = new URLSearchParams(location.search);
		function json(key) {
			try {
				return JSON.parse(p.get(key) || "{}") || {};
			} catch (e) {
				return {};
			}
		}
		this.state = {
			field_filters: json("field_filters"),
			attribute_filters: json("attribute_filters"),
			search: p.get("search") || "",
			sort: p.get("sort") || "ranking",
			price_min: p.get("price_min") || "",
			price_max: p.get("price_max") || "",
			in_stock: p.get("in_stock") || "",
			start: parseInt(p.get("start"), 10) || 0,
		};
	};

	Listing.prototype.url = function (start) {
		var s = this.state, p = new URLSearchParams();
		if (s.search) p.set("search", s.search);
		if (Object.keys(s.field_filters).length) p.set("field_filters", JSON.stringify(s.field_filters));
		if (Object.keys(s.attribute_filters).length) p.set("attribute_filters", JSON.stringify(s.attribute_filters));
		if (s.sort && s.sort !== "ranking") p.set("sort", s.sort);
		if (s.price_min) p.set("price_min", s.price_min);
		if (s.price_max) p.set("price_max", s.price_max);
		if (s.in_stock) p.set("in_stock", "1");
		if (start) p.set("start", start);
		var q = p.toString();
		return location.pathname + (q ? "?" + q : "");
	};

	Listing.prototype.syncInputs = function () {
		var s = this.state;
		if (this.form) {
			$all("input[type=checkbox]", this.form).forEach(function (input) {
				var parts = input.name.split(":");
				if (input.name === "in_stock") {
					input.checked = !!s.in_stock;
					return;
				}
				var bag = parts[0] === "attr" ? s.attribute_filters : s.field_filters;
				var values = bag[parts.slice(1).join(":")] || [];
				input.checked = values.indexOf(input.value) !== -1;
			});
			["price_min", "price_max"].forEach(function (name) {
				var input = this.form.querySelector('[name="' + name + '"]');
				if (input) input.value = s[name];
			}, this);
		}
		if (this.sort) this.sort.value = s.sort;
		var count = Object.keys(s.field_filters).reduce(function (n, k) { return n + s.field_filters[k].length; }, 0) +
			Object.keys(s.attribute_filters).reduce(function (n, k) { return n + s.attribute_filters[k].length; }, 0) +
			(s.price_min || s.price_max ? 1 : 0) + (s.in_stock ? 1 : 0);
		if (this.active) {
			this.active.textContent = String(count);
			this.active.hidden = count === 0;
		}
	};

	Listing.prototype.readInputs = function () {
		var s = this.state;
		s.field_filters = {};
		s.attribute_filters = {};
		$all("input[type=checkbox]:checked", this.form).forEach(function (input) {
			if (input.name === "in_stock") return;
			var parts = input.name.split(":");
			var bag = parts[0] === "attr" ? s.attribute_filters : s.field_filters;
			var key = parts.slice(1).join(":");
			(bag[key] = bag[key] || []).push(input.value);
		});
		var stock = this.form.querySelector('[name="in_stock"]');
		s.in_stock = stock && stock.checked ? "1" : "";
		var min = this.form.querySelector('[name="price_min"]');
		var max = this.form.querySelector('[name="price_max"]');
		s.price_min = min ? min.value.trim() : "";
		s.price_max = max ? max.value.trim() : "";
	};

	Listing.prototype.update = function (start) {
		this.state.start = start || 0;
		history.pushState(null, "", this.url(this.state.start));
		this.syncInputs();
		this.load();
	};

	Listing.prototype.bind = function () {
		var me = this;
		if (this.form) {
			this.form.addEventListener("change", function (e) {
				if (e.target.type === "number") return; // applied with the button
				me.readInputs();
				me.update(0);
			});
			this.form.addEventListener("submit", function (e) {
				e.preventDefault();
				me.readInputs();
				me.update(0);
			});
		}
		if (this.sort) {
			this.sort.addEventListener("change", function () {
				me.state.sort = me.sort.value;
				me.update(0);
			});
		}
		$all("[data-ps-view]", this.root).forEach(function (btn) {
			btn.addEventListener("click", function () { me.setView(btn.dataset.psView, true); });
		});
		this.pager.addEventListener("click", function (e) {
			var link = e.target.closest("a[data-start]");
			if (!link) return;
			e.preventDefault();
			me.update(parseInt(link.dataset.start, 10));
			me.root.scrollIntoView({ behavior: "smooth", block: "start" });
		});
		var retry = this.root.querySelector("[data-ps-retry]");
		if (retry) retry.addEventListener("click", function () { me.load(); });
		window.addEventListener("popstate", function () {
			me.readUrl();
			me.syncInputs();
			me.load();
		});
	};

	Listing.prototype.storedView = function () {
		try {
			return localStorage.getItem("ps_view") || "grid";
		} catch (e) {
			return "grid";
		}
	};

	Listing.prototype.setView = function (view, save) {
		this.results.classList.toggle("ps-grid--list", view === "list");
		$all("[data-ps-view]", this.root).forEach(function (b) {
			b.setAttribute("aria-pressed", b.dataset.psView === view ? "true" : "false");
		});
		if (save) {
			try {
				localStorage.setItem("ps_view", view);
			} catch (e) {
				/* view preference is a convenience only */
			}
		}
	};

	Listing.prototype.load = function () {
		var me = this, id = ++this.request, s = this.state;
		this.results.setAttribute("aria-busy", "true");
		this.results.innerHTML = this.skeleton;
		this.results.hidden = false;
		this.empty.hidden = true;
		this.error.hidden = true;

		frappe.call({
			method: "prime_store.api.get_product_filter_data",
			type: "GET",
			args: {
				query_args: JSON.stringify({
					field_filters: s.field_filters,
					attribute_filters: s.attribute_filters,
					search: s.search,
					sort: s.sort,
					price_min: s.price_min,
					price_max: s.price_max,
					in_stock: s.in_stock,
					start: s.start,
					item_group: me.itemGroup,
				}),
			},
			callback: function (r) {
				if (id !== me.request) return;
				var data = r && r.message;
				if (!data || data.exc) return me.fail();
				me.render(data);
			},
			error: function () {
				if (id === me.request) me.fail();
			},
		});
	};

	Listing.prototype.fail = function () {
		this.results.hidden = true;
		this.results.setAttribute("aria-busy", "false");
		this.pager.hidden = true;
		this.error.hidden = false;
	};

	Listing.prototype.render = function (data) {
		this.results.setAttribute("aria-busy", "false");
		this.total.textContent = data.items_count === 1
			? T.products_one
			: (T.products_many || "{0}").replace("{0}", data.items_count);

		if (data.price_range && this.form) {
			var min = this.form.querySelector('[name="price_min"]');
			var max = this.form.querySelector('[name="price_max"]');
			if (min) min.placeholder = Math.floor(data.price_range[0]);
			if (max) max.placeholder = Math.ceil(data.price_range[1]);
		}

		this.renderSubcats(data.sub_categories || []);

		if (!data.items_count || !data.html.trim()) {
			this.results.hidden = true;
			this.pager.hidden = true;
			this.empty.hidden = false;
			return;
		}
		this.results.innerHTML = data.html;
		this.renderPager(data.items_count, data.page_length, data.start);
	};

	Listing.prototype.renderSubcats = function (cats) {
		this.subcats.hidden = !cats.length;
		this.subcats.innerHTML = "";
		cats.forEach(function (c) {
			var a = document.createElement("a");
			a.className = "ps-pill";
			a.href = "/" + (c.route || "");
			a.textContent = c.name;
			this.subcats.appendChild(a);
		}, this);
	};

	Listing.prototype.renderPager = function (count, size, start) {
		var pages = Math.ceil(count / size), current = Math.floor(start / size);
		this.pager.innerHTML = "";
		this.pager.hidden = pages < 2;
		if (pages < 2) return;
		var me = this;

		function link(page, label, aria, cls) {
			var a = document.createElement("a");
			a.href = me.url(page * size);
			a.dataset.start = page * size;
			a.className = "ps-pager__link" + (cls ? " " + cls : "");
			a.innerHTML = label;
			a.setAttribute("aria-label", aria);
			if (page === current) a.setAttribute("aria-current", "page");
			me.pager.appendChild(a);
		}
		function gap() {
			var span = document.createElement("span");
			span.className = "ps-pager__gap";
			span.textContent = "…";
			me.pager.appendChild(span);
		}
		var chevron = '<svg class="ps-i ps-i--chevron %s" aria-hidden="true"><use href="#ps-i-chevron"></use></svg>';
		if (current > 0) link(current - 1, chevron.replace("%s", "ps-flip"), T.prev, "ps-pager__step");
		for (var i = 0; i < pages; i++) {
			if (i === 0 || i === pages - 1 || Math.abs(i - current) <= 1) {
				link(i, String(i + 1), (T.page || "{0}").replace("{0}", i + 1));
			} else if (i === 1 || i === pages - 2) {
				gap();
			}
		}
		if (current < pages - 1) link(current + 1, chevron.replace("%s", ""), T.next, "ps-pager__step");
	};

	/* ---------- Webshop pages we keep but polish ---------- */

	function addShopLinkToEmptyStates() {
		$all(".cart-empty").forEach(function (box) {
			if (box.querySelector("[data-ps-shop]")) return;
			var a = document.createElement("a");
			a.className = "ps-btn";
			a.href = T.shop_url || "/all-products";
			a.dataset.psShop = "1";
			a.textContent = T.continue;
			box.appendChild(a);
		});
	}

	ready(function () {
		try {
			var strings = document.getElementById("ps-i18n");
			T = JSON.parse((strings && strings.dataset.strings) || "{}");
		} catch (e) {
			T = {};
		}
		var main = document.querySelector("main") || document.querySelector(".page-content-wrapper");
		if (main && !document.getElementById("ps-main")) main.id = "ps-main";

		hookWebshopCounts();
		updateCounts();
		initDrawers();
		initActions();
		$all("[data-ps-menu]").forEach(initCategoryMenu);
		$all("[data-ps-slider]").forEach(initSlider);
		$all("[data-ps-countdown]").forEach(initCountdown);
		$all("[data-ps-gallery]").forEach(initGallery);
		$all("[data-ps-listing]").forEach(function (root) { new Listing(root); });
		addShopLinkToEmptyStates();
	});
})();
