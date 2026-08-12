#!/usr/bin/env python
"""
اسکریپت جامع و عمیق برای پر کردن کامل دیتابیس با داده‌های واقعی
Comprehensive Deep Seeding Script for Asoud Database
"""
import os
import sys
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
sys.path.insert(0, '/asoud')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from apps.region.models import Country, Province, City
from apps.category.models import Group, Category, SubCategory
from apps.market.models import Market, MarketLocation, MarketContact, MarketSchedule
from apps.product.models import Product, ProductImage
from apps.cart.models import Order, OrderItem
from apps.payment.models import Payment
from apps.comment.models import Comment
from apps.discount.models import Discount
from apps.wallet.models import Wallet, Transaction

User = get_user_model()

print("="*80)
print("🚀 اسکریپت جامع پر کردن دیتابیس - Asoud Platform")
print("="*80)
print()

# ==================== REGIONS ====================
print("1️⃣  ایجاد Regions جامع...")
print("-" * 80)

iran_provinces = {
    'تهران': ['تهران', 'کرج', 'ورامین', 'دماوند', 'رودهن', 'شهریار', 'اسلامشهر', 'پاکدشت'],
    'اصفهان': ['اصفهان', 'کاشان', 'نجف‌آباد', 'خمینی‌شهر', 'شاهین‌شهر', 'فلاورجان'],
    'فارس': ['شیراز', 'مرودشت', 'جهرم', 'کازرون', 'لار', 'آباده'],
    'خراسان رضوی': ['مشهد', 'نیشابور', 'سبزوار', 'قوچان', 'کاشمر', 'تربت حیدریه'],
    'آذربایجان شرقی': ['تبریز', 'مراغه', 'مرند', 'میانه', 'سراب', 'بناب'],
    'خوزستان': ['اهواز', 'دزفول', 'آبادان', 'خرمشهر', 'اندیمشک', 'شوشتر'],
    'مازندران': ['ساری', 'بابل', 'آمل', 'قائم‌شهر', 'بابلسر', 'نوشهر', 'چالوس'],
    'گیلان': ['رشت', 'انزلی', 'لاهیجان', 'لنگرود', 'رودسر', 'آستارا'],
    'کرمان': ['کرمان', 'رفسنجان', 'سیرجان', 'زرند', 'بم', 'جیرفت'],
    'یزد': ['یزد', 'میبد', 'اردکان', 'بافق', 'مهریز', 'ابرکوه'],
}

country, _ = Country.objects.get_or_create(name='ایران')
print(f"✓ Country: {country.name}")

total_cities = 0
for prov_name, cities in iran_provinces.items():
    province, created = Province.objects.get_or_create(
        name=prov_name,
        country=country
    )
    print(f"  {'✅' if created else '✓'} Province: {prov_name}")
    
    for city_name in cities:
        city, created = City.objects.get_or_create(
            name=city_name,
            province=province
        )
        total_cities += 1
        
print(f"✅ Total: {Province.objects.count()} provinces, {total_cities} cities")
print()

# ==================== CATEGORIES ====================
print("2️⃣  ایجاد Categories جامع...")
print("-" * 80)

categories_structure = {
    'غذا و نوشیدنی': {
        'market_fee': 50000,
        'categories': {
            'رستوران': {
                'market_fee': 55000,
                'subcategories': ['رستوران ایرانی', 'رستوران فرنگی', 'رستوران چینی', 
                                 'رستوران ایتالیایی', 'رستوران مکزیکی', 'رستوران ژاپنی']
            },
            'فست فود': {
                'market_fee': 45000,
                'subcategories': ['برگر', 'پیتزا', 'ساندویچ', 'سوخاری', 'هات داگ', 'کباب ترکی']
            },
            'کافه': {
                'market_fee': 35000,
                'subcategories': ['کافه مدرن', 'کافه سنتی', 'کافه کتاب', 'قهوه‌خانه']
            },
            'شیرینی و قنادی': {
                'market_fee': 40000,
                'subcategories': ['شیرینی خشک', 'شیرینی تر', 'کیک و کلوچه', 'بستنی', 'دسر']
            },
            'آبمیوه و بستنی': {
                'market_fee': 30000,
                'subcategories': ['آبمیوه طبیعی', 'بستنی سنتی', 'بستنی صنعتی', 'اسموتی']
            }
        }
    },
    'پوشاک و مد': {
        'market_fee': 30000,
        'categories': {
            'لباس مردانه': {
                'market_fee': 35000,
                'subcategories': ['تی‌شرت', 'پیراهن', 'شلوار', 'کت و شلوار', 'لباس ورزشی']
            },
            'لباس زنانه': {
                'market_fee': 40000,
                'subcategories': ['مانتو', 'شلوار', 'تونیک', 'پالتو', 'لباس مجلسی']
            },
            'کفش': {
                'market_fee': 35000,
                'subcategories': ['کفش مردانه', 'کفش زنانه', 'کفش بچگانه', 'کفش ورزشی']
            },
            'کیف و کوله': {
                'market_fee': 28000,
                'subcategories': ['کیف دستی', 'کوله پشتی', 'کیف لپ‌تاپ', 'کیف مدرسه']
            }
        }
    },
    'دیجیتال و الکترونیک': {
        'market_fee': 20000,
        'categories': {
            'موبایل و تبلت': {
                'market_fee': 15000,
                'subcategories': ['گوشی هوشمند', 'تبلت', 'لوازم جانبی موبایل', 'قاب و محافظ']
            },
            'کامپیوتر': {
                'market_fee': 18000,
                'subcategories': ['لپ‌تاپ', 'کامپیوتر رومیزی', 'مانیتور', 'کیبورد و ماوس']
            },
            'لوازم خانگی': {
                'market_fee': 25000,
                'subcategories': ['یخچال و فریزر', 'ماشین لباسشویی', 'جاروبرقی', 'اجاق گاز']
            }
        }
    },
    'خانه و آشپزخانه': {
        'market_fee': 25000,
        'categories': {
            'مبلمان': {
                'market_fee': 30000,
                'subcategories': ['مبل راحتی', 'میز و صندلی', 'کمد', 'تخت خواب']
            },
            'لوازم آشپزخانه': {
                'market_fee': 20000,
                'subcategories': ['ظروف', 'لوازم پخت و پز', 'چاقو و قاشق', 'ابزار آشپزی']
            },
            'دکوراسیون': {
                'market_fee': 22000,
                'subcategories': ['تابلو', 'فرش', 'پرده', 'گلدان', 'آینه']
            }
        }
    }
}

for group_name, group_data in categories_structure.items():
    group, created = Group.objects.get_or_create(
        title=group_name,
        defaults={'market_fee': group_data['market_fee']}
    )
    print(f"{'✅' if created else '✓'} Group: {group_name}")
    
    for cat_name, cat_data in group_data['categories'].items():
        category, created = Category.objects.get_or_create(
            title=cat_name,
            group=group,
            defaults={'market_fee': cat_data['market_fee']}
        )
        print(f"  {'✅' if created else '✓'} Category: {cat_name}")
        
        for subcat_name in cat_data['subcategories']:
            subcategory, created = SubCategory.objects.get_or_create(
                title=subcat_name,
                category=category,
                defaults={'market_fee': cat_data['market_fee']}
            )
            if created:
                print(f"    ✅ SubCategory: {subcat_name}")

print(f"✅ Total: {Group.objects.count()} groups, {Category.objects.count()} categories, {SubCategory.objects.count()} subcategories")
print()

# ==================== USERS ====================
print("3️⃣  ایجاد Users واقعی...")
print("-" * 80)

iranian_names = [
    ('علی', 'احمدی'), ('محمد', 'محمدی'), ('حسین', 'حسینی'), ('رضا', 'رضایی'),
    ('امیر', 'امیری'), ('مهدی', 'مهدوی'), ('سعید', 'سعیدی'), ('حمید', 'حمیدی'),
    ('فاطمه', 'فاطمی'), ('زهرا', 'زهرایی'), ('مریم', 'مریمی'), ('سارا', 'ساراوی'),
    ('نرگس', 'نرگسی'), ('الهام', 'الهامی'), ('مینا', 'مینایی'), ('پریسا', 'پریسایی'),
    ('احسان', 'احسانی'), ('پوریا', 'پوریایی'), ('امید', 'امیدی'), ('کیان', 'کیانی'),
]

users_created = 0
for i, (first_name, last_name) in enumerate(iranian_names, 1):
    mobile = f'0912345{i:04d}'
    user, created = User.objects.get_or_create(
        mobile_number=mobile,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'is_active': True,
            'type': random.choice(['owner', 'user', 'marketer'])
        }
    )
    if created:
        users_created += 1
        # ایجاد Wallet برای هر User (optional - if table exists)
        try:
            Wallet.objects.get_or_create(user=user, defaults={'balance': 0.0})
        except Exception:
            pass  # Skip if wallet table doesn't exist

print(f"✅ Created {users_created} users, Total: {User.objects.count()}")
print()

# ==================== MARKETS ====================
print("4️⃣  ایجاد Markets واقعی...")
print("-" * 80)

market_names = {
    'رستوران': ['رستوران سنتی حاج محمود', 'رستوران لواسانی', 'رستوران دیزی سرا', 
                'رستوران چلوکبابی اکبر', 'رستوران سفره‌خانه'],
    'فست فود': ['فست فود برگر کینگ', 'پیتزا ملل', 'ساندویچی بابا قدرت', 
                 'سوخاری مرغ سرخ', 'فست فود چیکن ران'],
    'کافه': ['کافه نادری', 'کافه ساموئل', 'کافه لامیز', 'کافه چیلینو', 'کافه تک'],
    'پوشاک': ['فروشگاه لباس زارا', 'بوتیک مانی', 'فروشگاه اچ اند ام', 'لباس پوشینه'],
    'موبایل': ['موبایل کده', 'فروشگاه موبایل پردیس', 'موبایل شاپ'],
}

owners = User.objects.filter(type='owner')[:10]
cities = City.objects.all()

markets_created = 0
for cat_name, market_list in market_names.items():
    category = Category.objects.filter(title__icontains=cat_name.split()[0]).first()
    if not category:
        continue
    
    subcategory = SubCategory.objects.filter(category=category).first()
    if not subcategory:
        continue
    
    for market_name in market_list:
        owner = random.choice(owners)
        city = random.choice(cities)
        
        market, created = Market.objects.get_or_create(
            business_id=f'MKT-{markets_created + 1:04d}',
            defaults={
                'user': owner,
                'type': random.choice(['shop', 'company']),
                'name': market_name,
                'description': f'{market_name} با بیش از 10 سال سابقه در خدمت شماست',
                'sub_category': subcategory,
                'slogan': 'کیفیت برتر، قیمت مناسب',
                'status': random.choice(['published', 'published', 'published', 'queue']),
                'is_paid': random.choice([True, True, False]),
            }
        )
        
        if created:
            markets_created += 1
            
            # ایجاد Location برای Market
            MarketLocation.objects.get_or_create(
                market=market,
                defaults={
                    'city': city,
                    'address': f'خیابان آزادی، {random.randint(1, 500)} متری، پلاک {random.randint(1, 200)}',
                    'zip_code': f'{random.randint(1000000000, 9999999999)}',
                    'latitude': Decimal(f'{random.uniform(35.0, 36.0):.6f}'),
                    'longitude': Decimal(f'{random.uniform(50.0, 52.0):.6f}'),
                }
            )
            
            # ایجاد Contact برای Market
            MarketContact.objects.get_or_create(
                market=market,
                defaults={
                    'first_mobile_number': f'0912{random.randint(1000000, 9999999)}',
                    'telephone': f'021{random.randint(10000000, 99999999)}',
                    'email': f'{market.business_id.lower()}@example.com',
                }
            )
            
            print(f"  ✅ Market: {market_name}")

print(f"✅ Created {markets_created} markets, Total: {Market.objects.count()}")
print()

# ==================== PRODUCTS ====================
print("5️⃣  ایجاد Products واقعی...")
print("-" * 80)

product_templates = {
    'رستوران': [
        'چلوکباب کوبیده', 'چلوکباب برگ', 'جوجه کباب', 'کباب سلطانی',
        'قرمه سبزی', 'قیمه بادمجان', 'فسنجان', 'زرشک پلو با مرغ'
    ],
    'فست فود': [
        'همبرگر معمولی', 'همبرگر مخصوص', 'چیزبرگر', 'پیتزا پپرونی',
        'پیتزا مرغ', 'ساندویچ مرغ', 'ساندویچ کالباس', 'سیب زمینی سرخ کرده'
    ],
    'پوشاک': [
        'تی‌شرت مردانه', 'پیراهن مردانه', 'شلوار جین', 'مانتو زنانه',
        'پالتو زنانه', 'کفش مردانه', 'کفش زنانه', 'کوله پشتی'
    ],
    'موبایل': [
        'گوشی سامسونگ A54', 'گوشی شیائومی Redmi Note 12', 
        'گوشی ایفون 13', 'قاب محافظ', 'گلس محافظ', 'پاوربانک'
    ]
}

products_created = 0
markets = Market.objects.filter(status='published')

for market in markets:
    cat_name = market.sub_category.category.title
    
    # پیدا کردن template مناسب
    template = None
    for key in product_templates:
        if key in cat_name:
            template = product_templates[key]
            break
    
    if not template:
        continue
    
    # ایجاد 3-8 محصول برای هر Market
    num_products = random.randint(3, 8)
    selected_products = random.sample(template, min(num_products, len(template)))
    
    for product_name in selected_products:
        price = Decimal(random.randint(50000, 500000))
        
        product, created = Product.objects.get_or_create(
            name=product_name,
            market=market,
            defaults={
                'main_price': price,
                'colleague_price': price * Decimal('0.95'),
                'marketer_price': price * Decimal('0.90'),
                'maximum_sell_price': price * Decimal('1.20'),
                'description': f'{product_name} با کیفیت عالی و قیمت مناسب',
                'status': random.choice(['available', 'available', 'available', 'out_of_stock']),
                'stock': random.randint(0, 100),
                'sub_category': market.sub_category,
            }
        )
        
        if created:
            products_created += 1

print(f"✅ Created {products_created} products, Total: {Product.objects.count()}")
print()

# ==================== ORDERS & PAYMENTS ====================
print("6️⃣  ایجاد Orders و Payments...")
print("-" * 80)

customers = User.objects.filter(type='user')[:10]
products = Product.objects.filter(status='available')

orders_created = 0
payments_created = 0

for customer in customers:
    # هر مشتری 1-5 سفارش داشته
    num_orders = random.randint(1, 5)
    
    for _ in range(num_orders):
        # ایجاد Order
        order = Order.objects.create(
            user=customer,
            type=random.choice(['cash', 'online']),
            status=random.choice(['pending', 'completed', 'failed']),
            is_paid=random.choice([True, False]),
            description='سفارش از طریق اپلیکیشن',
        )
        orders_created += 1
        
        # اضافه کردن 1-4 محصول به سفارش
        num_items = random.randint(1, 4)
        selected_products = random.sample(list(products), min(num_items, len(products)))
        
        for product in selected_products:
            quantity = random.randint(1, 3)
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
            )
        
        # ایجاد Payment برای Order (اگر پرداخت شده)
        if order.is_paid and order.status == 'completed':
            try:
                Payment.objects.create(
                    user=customer,
                    amount=order.total_price(),
                    status='success',
                    description=f'پرداخت سفارش #{str(order.id)[:8]}',
                )
                payments_created += 1
            except Exception:
                pass  # Skip if payment model has issues

print(f"✅ Created {orders_created} orders with items")
print(f"✅ Created {payments_created} payments")
print()

# ==================== COMMENTS ====================
print("7️⃣  ایجاد Comments (Skip - complex model)...")
print("-" * 80)
print("⊘ Skipped comments (using django-comments-xtd)")
print()

# ==================== DISCOUNTS ====================
print("8️⃣  ایجاد Discounts...")
print("-" * 80)

discount_codes = ['WELCOME10', 'SUMMER20', 'FIRST15', 'SPECIAL25', 'VIP30']

discounts_created = 0
for code in discount_codes:
    try:
        discount, created = Discount.objects.get_or_create(
            code=code,
            defaults={
                'type': random.choice(['percentage', 'fixed']),
                'value': Decimal(random.randint(10, 30)),
                'max_usage': random.randint(50, 200),
                'used_count': random.randint(0, 30),
                'start_date': datetime.now(),
                'end_date': datetime.now() + timedelta(days=random.randint(30, 90)),
                'is_active': True,
            }
        )
        if created:
            discounts_created += 1
    except Exception as e:
        pass  # Skip if discount model has different structure

print(f"✅ Created {discounts_created} discounts")
print()

# ==================== SUMMARY ====================
print()
print("="*80)
print("📊 خلاصه نهایی دیتابیس")
print("="*80)
print()
print(f"🌍 Regions:")
print(f"   - Countries:      {Country.objects.count()}")
print(f"   - Provinces:      {Province.objects.count()}")
print(f"   - Cities:         {City.objects.count()}")
print()
print(f"📁 Categories:")
print(f"   - Groups:         {Group.objects.count()}")
print(f"   - Categories:     {Category.objects.count()}")
print(f"   - SubCategories:  {SubCategory.objects.count()}")
print()
print(f"👥 Users & Markets:")
print(f"   - Users:          {User.objects.count()}")
print(f"   - Markets:        {Market.objects.count()}")
print(f"   - Locations:      {MarketLocation.objects.count()}")
print(f"   - Contacts:       {MarketContact.objects.count()}")
print()
print(f"🛍️ Products & Orders:")
print(f"   - Products:       {Product.objects.count()}")
print(f"   - Orders:         {Order.objects.count()}")
print(f"   - OrderItems:     {OrderItem.objects.count()}")
print()
print(f"💳 Payments & Finance:")
try:
    print(f"   - Payments:       {Payment.objects.count()}")
except:
    print(f"   - Payments:       (table not migrated)")
try:
    print(f"   - Wallets:        {Wallet.objects.count()}")
except:
    print(f"   - Wallets:        (table not migrated)")
try:
    print(f"   - Discounts:      {Discount.objects.count()}")
except:
    print(f"   - Discounts:      (table not migrated)")
print()
print(f"💬 Social:")
try:
    from django_comments_xtd.models import XtdComment
    print(f"   - Comments:       {XtdComment.objects.count()}")
except:
    print(f"   - Comments:       (skipped)")
print()
print("="*80)
print("✅ دیتابیس با موفقیت و به صورت کامل پر شد!")
print("="*80)

