# Prime Store

واجهة متجر إلكترونيات لـ ERPNext v16 (Webshop). كل البيانات من النظام: المنتجات والأسعار وقواعد التسعير والمخزون والسلة والمفضلة.

## بيغيّر إيه

| الصفحة | الملف |
|---|---|
| الهيدر (بحث، حساب، مفضلة، سلة، قائمة الأقسام، قائمة الموبايل) | `templates/includes/navbar/navbar.html` |
| الفوتر | `templates/includes/footer/footer.html` |
| الرئيسية `/store-home` | `www/store-home.html`, `www/store_home.py` |
| كل المنتجات `/all-products` | `www/all-products/` |
| صفحة القسم (Item Group) | `templates/generators/item_group.html` |
| صفحة المنتج | `templates/generators/item/item.html`, `item_image.html`, `item_details.html`, `item_add_to_cart.html` |
| كارت المنتج (مشترك) | `templates/includes/prime_store/macros.html` |
| بيانات القائمة: ترتيب، فلتر سعر، فلتر توفر | `api.py` (`prime_store.api.get_product_filter_data`) |

لازم `prime_store` يتسطّب **بعد** `webshop`. ملفاته اللي بنفس المسار بتغطي على ملفات Webshop.
السلة وعرض السعر والطلبات صفحات Webshop نفسها. بنغيّر شكلها بالـ CSS بس، ومنطقها زي ما هو.

## الإعدادات اللي بتأثر على الواجهة

| المطلوب | مكانه |
|---|---|
| اسم المتجر واللوجو | Website Settings: App Name / Brand HTML / Banner Image / Footer Logo / Copyright / Address |
| لينكات إضافية في الهيدر والفوتر | Website Settings: Top Bar Items / Footer Items |
| التليفون والإيميل في الفوتر | Contact Us Settings |
| السلة، والدفع أو طلب عرض سعر، والمفضلة، والمخزون، وعدد المنتجات في الصفحة | Webshop Settings |
| شارة الكارت (وصل حديثًا، رائج، حصري، الأكثر مبيعًا، تخفيض) | Website Item: Store Badge |
| الأقسام المعروضة | Item Group: Show in Website |
| شرائح البانر | Website Slideshow باسم **Home Hero** |
| العرضين الجانبيين جنب البانر | Website Slideshow باسم **Home Offers** (أول شريحتين) |
| لون العميل | Website Settings > Head HTML: `<style>:root{--ps-primary:#0b7a5b;--ps-primary-dark:#075a43}</style>` |

إعدادات في `site_config.json`. لو أي قيمة منهم مش متحددة، الجزء بتاعها مش بيظهر:

```bash
bench --site SITE set-config prime_store_announcement "خصم 20% على السماعات"
bench --site SITE set-config prime_store_deal_end "2026-12-31T23:59:00"
bench --site SITE set-config -p prime_store_perks '["توصيل خلال 48 ساعة", "دعم فني 7 أيام"]'
bench --site SITE set-config -p prime_store_social '{"facebook": "https://facebook.com/...", "instagram": "https://instagram.com/..."}'
bench --site SITE set-config prime_store_shop_url "/all-products"
```

ماتكتبش مزايا في `prime_store_perks` إلا لو المتجر بيقدّمها فعلًا، زي التوصيل والإرجاع.

## ملاحظات

- فلتر السعر والترتيب بالسعر بيعتمدوا على سعر قائمة الأسعار (Price List) اللي في Webshop Settings. السعر اللي بيظهر في الكارت هو السعر النهائي بعد قواعد التسعير.
- زرار "أضف للسلة" بيظهر بنفس شروط Webshop: لازم يكون للمنتج سعر، ويكون متوفر في المخزون أو `Allow items not in stock` مفعّلة.
- الخط (IBM Plex Sans Arabic) بيتحمّل من Google Fonts.
- الصور والأيقونات لازم تكون ملكك. ماتنسخش ملفات من themes مدفوعة أو من مواقع تانية.
