(function () {
	"use strict";

	function ready(fn) {
		if (document.readyState !== "loading") fn();
		else document.addEventListener("DOMContentLoaded", fn);
	}

	function initSlider(root) {
		var slides = root.querySelectorAll(".ps-slide");
		var dots = root.querySelectorAll("[data-ps-dot]");
		if (slides.length < 2) return;
		var index = 0, timer = null;
		var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

		function show(i) {
			index = (i + slides.length) % slides.length;
			slides.forEach(function (s, n) { s.classList.toggle("is-active", n === index); });
			dots.forEach(function (d, n) { d.classList.toggle("is-active", n === index); });
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

	function initNewsletter(form) {
		var msg = document.querySelector("[data-ps-msg]");
		form.addEventListener("submit", function (e) {
			e.preventDefault();
			var input = form.querySelector("input");
			if (!input.checkValidity()) { input.reportValidity(); return; }
			if (!window.frappe || !frappe.call) return;
			frappe.call({
				method: "frappe.email.doctype.newsletter.newsletter.subscribe",
				args: { email: input.value },
				callback: function () { msg.textContent = "✓"; input.value = ""; },
				error: function () { msg.textContent = "!"; },
			});
		});
	}

	ready(function () {
		document.querySelectorAll("[data-ps-slider]").forEach(initSlider);
		document.querySelectorAll("[data-ps-countdown]").forEach(initCountdown);
		document.querySelectorAll("[data-ps-newsletter]").forEach(initNewsletter);
	});
})();
