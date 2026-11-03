# Prime Store

قالب متجر إلكترونيات لـ ERPNext (Webshop). بيتثبت كـ Frappe App على أي عدد من العملاء، والتحديثات بتتسحب من GitHub.

## التركيب عند عميل جديد

```bash
cd ~/frappe-bench
bench get-app https://github.com/USERNAME/prime_store --branch main
bench --site CLIENT_SITE install-app prime_store
bench --site CLIENT_SITE migrate
bench build --app prime_store
bench restart
```

لو الـ repo خاص: استخدم Deploy Key أو `https://TOKEN@github.com/USERNAME/prime_store`.

## التحديث لكل العملاء على نفس السيرفر

```bash
./scripts/update_all_sites.sh ~/frappe-bench main
```

لإصدار معين: `./scripts/update_all_sites.sh ~/frappe-bench v0.2.0`

## تخصيص كل عميل (بدون ما تلمس الكود)

| المطلوب | مكانه |
|---|---|
| اللوجو والاسم والفوتر | Website Settings |
| لون العميل | Website Settings > Head HTML: `<style>:root{--ps-primary:#0b7a5b;--ps-primary-dark:#075a43}</style>` |
| شرائح الهيرو | Website Slideshow باسم **Home Hero** (صورة + عنوان + وصف + رابط) |
| شريط الإعلان | `bench --site SITE set-config prime_store_announcement "خصم 20%"` |
| عداد العرض | `bench --site SITE set-config prime_store_deal_end "2026-12-31T23:59:00"` (من غير القيمة دي القسم مخفي) |
| رابط المتجر | `prime_store_shop_url` (الافتراضي `/all-products`) |
| المنتجات والأقسام والماركات | Website Item / Item Group (Show in Website) / Brand |
| السعر المعروض | Price List المحددة في Webshop Settings |

الصفحة الرئيسية على المسار `/store-home`، والتركيب بيضبطها كـ Home Page لو العميل ماحددش واحدة. لو ماظهرتش: Website Settings > Home Page = `store-home`.

## إصدار نسخة جديدة

```bash
# عدّل __version__ في prime_store/__init__.py
git commit -am "Release 0.2.0" && git tag v0.2.0 && git push && git push --tags
```

## ملاحظات

- الأصول (الصور والأيقونات) لازم تكون بتاعتك. ماتنسخش ملفات من themes مدفوعة.
- الخط بيتحمّل من Google Fonts. لو العميل عايز استضافة محلية، حط الملفات في `public/` وغيّر `@import`.
- جرّب أي تحديث على موقع تجريبي قبل ما تنزله على العملاء.
