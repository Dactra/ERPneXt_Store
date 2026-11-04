# Prime Store

إضافة (Frappe app) بتغيّر شكل متجر ERPNext لواجهة متجر إلكترونيات احترافية، عربي وإنجليزي (RTL/LTR) ومتجاوبة مع الموبايل.
كل البيانات من النظام نفسه: المنتجات، والأسعار، وقواعد التسعير، والمخزون، والسلة، والمفضلة. مفيش بيانات ثابتة في الكود.

- **الإصدار المدعوم:** ERPNext / Frappe **v16** مع تطبيق **Webshop**.
- **الرخصة:** MIT.

## التركيب على أي سيستم ERPNext

لازم يكون Webshop متسطّب الأول. Prime Store لازم يتسطّب **بعده**، عشان ملفاته تغطي على ملفات Webshop.

```bash
# 1) Webshop (لو مش موجود)
bench get-app webshop https://github.com/frappe/webshop
bench --site SITE install-app webshop

# 2) Prime Store (الريبو Private: استخدم توكن GitHub عنده صلاحية قراءة الريبو)
bench get-app prime_store https://github.com/Dactra/ERPneXt_Store
bench --site SITE install-app prime_store
bench build --app prime_store
bench --site SITE clear-cache && bench --site SITE clear-website-cache
```

> لو الريبو Private، `bench get-app` هيطلب اسم المستخدم وتوكن GitHub (Personal Access Token). ماتحطش التوكن جوه الرابط في أوامر بتتسجّل.

### التركيب في Docker (frappe_docker)

ضيف الإضافة لـ `apps.json` **بعد** `webshop`:

```json
{ "name": "prime_store", "url": "https://github.com/Dactra/ERPneXt_Store", "ref": "main" }
```

وبعدين ابني الـ image بالطريقة العادية وشغّل `install-app` على الموقع.

### بعد التركيب

- الصفحة الرئيسية بتتظبط على `/store-home`، **بس لو** مفيش صفحة رئيسية متحددة قبل كده.
- بيتعمل حقل **Store Badge** في Website Item، وصفحة إعدادات **Prime Store Settings**.
- عند إلغاء التركيب (`uninstall-app`) الصفحة الرئيسية بترجع زي ما كانت.

### التحديث

```bash
bench update --apps prime_store   # أو: cd apps/prime_store && git pull
bench --site SITE migrate && bench build --app prime_store
```

## الإعدادات

### Prime Store Settings (من الديسك)

ابحث عن **Prime Store Settings** في ERPNext:

| الإعداد | بيعمل إيه |
|---|---|
| Header Perks | سطر لكل ميزة (توصيل، إرجاع...). بتظهر في الشريط الأزرق فوق الهيدر. اكتب بس اللي المتجر بيقدّمه فعلًا |
| Homepage Announcement | سطر إعلان في أول الرئيسية |
| Shop Page URL | رابط صفحة المتجر (الافتراضي `/all-products`) |
| Hero Slideshow / Offer Banners Slideshow | Website Slideshow للبانر والعرضين الجانبيين. لو فاضيين، بيتستخدم **Home Hero** و**Home Offers** لو موجودين |
| Deal Countdown Ends | عدّاد "عرض اليوم" لحد الوقت ده. لو فاضي، القسم مش بيظهر |
| Colour Swatch Attribute | خاصية النسخ اللي بتظهر كدواير ألوان على الكارت (الافتراضي Color) |
| Enable Product Compare | زرار المقارنة وصفحة `/compare` |
| Social Links | فيسبوك، انستجرام، تيك توك، X، يوتيوب، واتساب في الفوتر |

### إعدادات ERPNext اللي بتأثر على الواجهة

| المطلوب | مكانه |
|---|---|
| اسم المتجر واللوجو | Website Settings: App Name / Brand HTML / Banner Image / Footer Logo / Copyright / Address |
| لينكات إضافية في الهيدر والفوتر | Website Settings: Top Bar Items / Footer Items |
| التليفون والإيميل | Contact Us Settings |
| السلة، والدفع أو طلب عرض سعر، والمفضلة، والمخزون، وعدد المنتجات في الصفحة | Webshop Settings |
| إخفاء النسخ من القائمة وفلاتر الخصائص (اللون، المقاس...) | Webshop Settings: Hide Variants / Filter Attributes |
| شارة الكارت (وصل حديثًا، رائج، حصري، الأكثر مبيعًا، تخفيض) | Website Item: Store Badge |
| وسوم الفلتر (Tags) | التاجز (Tags) بتاعة Website Item |
| الأقسام المعروضة وشجرتها | Item Group: Show in Website (وInclude Descendants للأقسام اللي تحتها أقسام) |
| لون المتجر | Website Settings > Head HTML: `<style>:root{--ps-primary:#0b7a5b;--ps-primary-dark:#075a43}</style>` |

> الإعدادات القديمة في `site_config.json` (`prime_store_perks`, `prime_store_social`، إلخ) لسه شغالة كبديل. أول `migrate` بينقلها لـ Prime Store Settings.

## بيغيّر إيه

| الصفحة | الملف |
|---|---|
| الهيدر (بحث، حساب، مفضلة، سلة، قائمة الأقسام، قائمة الموبايل) | `templates/includes/navbar/navbar.html` |
| الفوتر | `templates/includes/footer/footer.html` |
| الرئيسية `/store-home` | `www/store-home.html`, `www/store_home.py` |
| كل المنتجات `/all-products` | `www/all-products/` |
| صفحة القسم (Item Group) | `templates/generators/item_group.html` |
| صفحة المنتج | `templates/generators/item/` |
| مقارنة المنتجات `/compare` | `www/compare.html`, `www/compare.py` |
| كارت المنتج (مشترك) | `templates/includes/prime_store/macros.html` |
| بيانات القائمة: ترتيب، فلاتر، ألوان، مقارنة | `api.py` |

السلة وعرض السعر والطلبات صفحات Webshop نفسها. بنغيّر شكلها بالـ CSS بس، ومنطقها زي ما هو.

## ملاحظات

- فلتر السعر والترتيب بالسعر بيعتمدوا على قائمة الأسعار (Price List) اللي في Webshop Settings. السعر اللي بيظهر في الكارت هو السعر النهائي بعد قواعد التسعير. المنتج اللي ليه نسخ بيظهر بـ "يبدأ من" أرخص نسخة.
- زرار "أضف للسلة" بيظهر بنفس شروط Webshop: لازم يكون للمنتج سعر، ويكون متوفر في المخزون أو `Allow items not in stock` مفعّلة.
- قايمة المقارنة بتتحفظ في متصفح الزائر (لحد 4 منتجات)، ورابط `/compare?items=...` ينفع يتبعت.
- الخط (IBM Plex Sans Arabic، رخصة OFL) متخزّن في `public/fonts` ومش بيتحمّل من Google، عشان سرعة الصفحة.
- الصور والأيقونات لازم تكون ملكك. ماتنسخش ملفات من themes مدفوعة أو من مواقع تانية.
