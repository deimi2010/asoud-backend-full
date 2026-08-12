#!/usr/bin/env python
"""
اسکریپت ایجاد داده‌های تست برای Market Location
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/asoud')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.region.models import Country, Province, City
from apps.category.models import Group, Category, SubCategory
from apps.market.models import Market
from apps.users.models import User

print("=" * 60)
print("🚀 ایجاد داده‌های تست")
print("=" * 60)
print()

# 1. ایجاد Region Data
print("1️⃣  ایجاد Region Data...")
country, created = Country.objects.get_or_create(name='Iran')
print(f"   {'✅ Created' if created else '✓ Exists'}: Country - {country.name} (ID: {country.id})")

province, created = Province.objects.get_or_create(name='Tehran', country=country)
print(f"   {'✅ Created' if created else '✓ Exists'}: Province - {province.name} (ID: {province.id})")

city, created = City.objects.get_or_create(name='Tehran', province=province)
print(f"   {'✅ Created' if created else '✓ Exists'}: City - {city.name} (ID: {city.id})")
print()

# 2. ایجاد Category Data  
print("2️⃣  ایجاد Category Data...")
group, created = Group.objects.get_or_create(
    title='خدمات',
    defaults={'market_fee': 100000}
)
print(f"   {'✅ Created' if created else '✓ Exists'}: Group - {group.title} (ID: {group.id})")

category, created = Category.objects.get_or_create(
    title='رستوران', 
    group=group,
    defaults={'market_fee': 50000}
)
print(f"   {'✅ Created' if created else '✓ Exists'}: Category - {category.title} (ID: {category.id})")

subcat, created = SubCategory.objects.get_or_create(
    title='فست فود', 
    category=category,
    defaults={'market_fee': 25000}
)
print(f"   {'✅ Created' if created else '✓ Exists'}: SubCategory - {subcat.title} (ID: {subcat.id})")
print()

# 3. بررسی User
print("3️⃣  بررسی User...")
user = User.objects.first()
if user:
    print(f"   ✓ Found User: {user.mobile_number} (ID: {user.id})")
else:
    print("   ❌ هیچ User ای وجود ندارد! باید اول login کنی")
    sys.exit(1)
print()

# 4. ایجاد Market
print("4️⃣  ایجاد Market...")
market, created = Market.objects.get_or_create(
    business_id='TEST-MARKET-001',
    defaults={
        'user': user,
        'type': 'shop',
        'name': 'تست رستوران',
        'description': 'رستوران تست برای آزمایش',
        'sub_category': subcat,
        'slogan': 'بهترین فست فود شهر',
    }
)
print(f"   {'✅ Created' if created else '✓ Exists'}: Market - {market.name} (ID: {market.id})")
print()

# نمایش خلاصه
print("=" * 60)
print("📋 خلاصه IDهای مورد نیاز برای Postman:")
print("=" * 60)
print(f"""
استفاده کن از این JSON در Postman:

{{
  "market": "{market.id}",
  "city": "{city.id}",
  "address": "tajrish",
  "zip_code": "9176666666",
  "latitude": 35.6892,
  "longitude": 51.3898
}}

""")
print("=" * 60)
print("✅ آماده است! حالا می‌تونی Location ایجاد کنی!")
print("=" * 60)

