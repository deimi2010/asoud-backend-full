"""
Management command to seed initial data for the application
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.category.models import Group, Category, SubCategory, ProductGroup, ProductCategory, ProductSubCategory
from apps.region.models import Country, Province, City
import uuid


class Command(BaseCommand):
    help = 'Seed initial data for the application'

    def handle(self, *args, **options):
        self.stdout.write('Starting to seed initial data...')
        
        with transaction.atomic():
            # Create countries and regions
            self.create_countries_and_regions()
            
            # Create groups
            self.create_groups()
            
            # Create categories
            self.create_categories()
            
            # Create subcategories
            self.create_subcategories()
            
            # Create product groups
            self.create_product_groups()
            
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded initial data!')
        )

    def create_countries_and_regions(self):
        """Create initial countries, provinces, and cities"""
        self.stdout.write('Creating countries and regions...')
        
        # Create Iran
        iran, created = Country.objects.get_or_create(
            name='ایران',
            defaults={'id': uuid.uuid4()}
        )
        self.stdout.write(f'  Iran: {"created" if created else "exists"}')
        
        # Create provinces
        provinces_data = [
            {'name': 'تهران', 'country': iran},
            {'name': 'اصفهان', 'country': iran},
            {'name': 'شیراز', 'country': iran},
            {'name': 'مشهد', 'country': iran},
            {'name': 'تبریز', 'country': iran},
        ]
        
        for prov_data in provinces_data:
            province, created = Province.objects.get_or_create(
                name=prov_data['name'],
                country=prov_data['country'],
                defaults={'id': uuid.uuid4()}
            )
            self.stdout.write(f'  {prov_data["name"]}: {"created" if created else "exists"}')
            
            # Create main city for each province
            city, created = City.objects.get_or_create(
                name=prov_data['name'],
                province=province,
                defaults={'id': uuid.uuid4()}
            )
            self.stdout.write(f'    {prov_data["name"]} city: {"created" if created else "exists"}')

    def create_groups(self):
        """Create initial groups"""
        self.stdout.write('Creating groups...')
        
        groups_data = [
            {'title': 'غذا و رستوران', 'market_fee': 5.000},
            {'title': 'پوشاک و مد', 'market_fee': 3.000},
            {'title': 'الکترونیک و دیجیتال', 'market_fee': 2.000},
            {'title': 'خودرو و موتورسیکلت', 'market_fee': 4.000},
            {'title': 'خانه و آشپزخانه', 'market_fee': 2.500},
            {'title': 'ورزش و تفریح', 'market_fee': 3.500},
            {'title': 'زیبایی و سلامت', 'market_fee': 4.500},
            {'title': 'کتاب و لوازم تحریر', 'market_fee': 1.500},
        ]
        
        for group_data in groups_data:
            group, created = Group.objects.get_or_create(
                title=group_data['title'],
                defaults={
                    'id': uuid.uuid4(),
                    'market_fee': group_data['market_fee']
                }
            )
            self.stdout.write(f'  {group_data["title"]}: {"created" if created else "exists"}')

    def create_categories(self):
        """Create initial categories"""
        self.stdout.write('Creating categories...')
        
        # Get groups
        food_group = Group.objects.get(title='غذا و رستوران')
        clothing_group = Group.objects.get(title='پوشاک و مد')
        electronics_group = Group.objects.get(title='الکترونیک و دیجیتال')
        home_group = Group.objects.get(title='خانه و آشپزخانه')
        
        # Food categories
        food_categories = [
            {'title': 'رستوران', 'group': food_group, 'market_fee': 5.000},
            {'title': 'فست فود', 'group': food_group, 'market_fee': 4.500},
            {'title': 'کافه', 'group': food_group, 'market_fee': 3.500},
            {'title': 'شیرینی و کیک', 'group': food_group, 'market_fee': 4.000},
            {'title': 'سوپرمارکت', 'group': food_group, 'market_fee': 2.000},
        ]
        
        # Clothing categories
        clothing_categories = [
            {'title': 'لباس مردانه', 'group': clothing_group, 'market_fee': 3.000},
            {'title': 'لباس زنانه', 'group': clothing_group, 'market_fee': 3.500},
            {'title': 'لباس بچه', 'group': clothing_group, 'market_fee': 2.500},
            {'title': 'کفش', 'group': clothing_group, 'market_fee': 3.000},
            {'title': 'اکسسوری', 'group': clothing_group, 'market_fee': 2.000},
        ]
        
        # Electronics categories
        electronics_categories = [
            {'title': 'موبایل و تبلت', 'group': electronics_group, 'market_fee': 1.500},
            {'title': 'لپ تاپ و کامپیوتر', 'group': electronics_group, 'market_fee': 2.000},
            {'title': 'لوازم جانبی', 'group': electronics_group, 'market_fee': 1.000},
            {'title': 'گیم و سرگرمی', 'group': electronics_group, 'market_fee': 2.500},
        ]
        
        # Home categories
        home_categories = [
            {'title': 'مبلمان', 'group': home_group, 'market_fee': 2.000},
            {'title': 'دکوراسیون', 'group': home_group, 'market_fee': 1.500},
            {'title': 'لوازم آشپزخانه', 'group': home_group, 'market_fee': 1.000},
            {'title': 'نور و روشنایی', 'group': home_group, 'market_fee': 1.500},
        ]
        
        all_categories = food_categories + clothing_categories + electronics_categories + home_categories
        
        for cat_data in all_categories:
            category, created = Category.objects.get_or_create(
                title=cat_data['title'],
                group=cat_data['group'],
                defaults={
                    'id': uuid.uuid4(),
                    'market_fee': cat_data['market_fee']
                }
            )
            self.stdout.write(f'  {cat_data["title"]}: {"created" if created else "exists"}')

    def create_subcategories(self):
        """Create initial subcategories"""
        self.stdout.write('Creating subcategories...')
        
        # Get categories
        restaurant_cat = Category.objects.get(title='رستوران')
        fastfood_cat = Category.objects.get(title='فست فود')
        cafe_cat = Category.objects.get(title='کافه')
        men_clothing_cat = Category.objects.get(title='لباس مردانه')
        women_clothing_cat = Category.objects.get(title='لباس زنانه')
        mobile_cat = Category.objects.get(title='موبایل و تبلت')
        
        # Restaurant subcategories
        restaurant_subcats = [
            {'title': 'رستوران ایرانی', 'category': restaurant_cat, 'market_fee': 5.500},
            {'title': 'رستوران فرنگی', 'category': restaurant_cat, 'market_fee': 6.000},
            {'title': 'رستوران چینی', 'category': restaurant_cat, 'market_fee': 5.000},
            {'title': 'رستوران ایتالیایی', 'category': restaurant_cat, 'market_fee': 5.500},
        ]
        
        # Fast food subcategories
        fastfood_subcats = [
            {'title': 'برگر و ساندویچ', 'category': fastfood_cat, 'market_fee': 4.000},
            {'title': 'پیتزا', 'category': fastfood_cat, 'market_fee': 4.500},
            {'title': 'کباب و جوجه', 'category': fastfood_cat, 'market_fee': 4.200},
            {'title': 'سوخاری', 'category': fastfood_cat, 'market_fee': 3.800},
        ]
        
        # Cafe subcategories
        cafe_subcats = [
            {'title': 'کافه سنتی', 'category': cafe_cat, 'market_fee': 3.000},
            {'title': 'کافه مدرن', 'category': cafe_cat, 'market_fee': 3.500},
            {'title': 'کافه کتاب', 'category': cafe_cat, 'market_fee': 2.800},
        ]
        
        # Men's clothing subcategories
        men_clothing_subcats = [
            {'title': 'تی‌شرت و پولو', 'category': men_clothing_cat, 'market_fee': 2.500},
            {'title': 'شلوار و جین', 'category': men_clothing_cat, 'market_fee': 3.000},
            {'title': 'کت و شلوار', 'category': men_clothing_cat, 'market_fee': 4.000},
            {'title': 'لباس ورزشی', 'category': men_clothing_cat, 'market_fee': 2.800},
        ]
        
        # Women's clothing subcategories
        women_clothing_subcats = [
            {'title': 'لباس مجلسی', 'category': women_clothing_cat, 'market_fee': 4.000},
            {'title': 'لباس روزمره', 'category': women_clothing_cat, 'market_fee': 3.200},
            {'title': 'لباس ورزشی', 'category': women_clothing_cat, 'market_fee': 3.000},
            {'title': 'لباس زیر', 'category': women_clothing_cat, 'market_fee': 2.500},
        ]
        
        # Mobile subcategories
        mobile_subcats = [
            {'title': 'گوشی هوشمند', 'category': mobile_cat, 'market_fee': 1.200},
            {'title': 'تبلت', 'category': mobile_cat, 'market_fee': 1.500},
            {'title': 'لوازم جانبی موبایل', 'category': mobile_cat, 'market_fee': 0.800},
            {'title': 'قاب و محافظ', 'category': mobile_cat, 'market_fee': 0.500},
        ]
        
        all_subcats = (restaurant_subcats + fastfood_subcats + cafe_subcats + 
                      men_clothing_subcats + women_clothing_subcats + mobile_subcats)
        
        for subcat_data in all_subcats:
            subcategory, created = SubCategory.objects.get_or_create(
                title=subcat_data['title'],
                category=subcat_data['category'],
                defaults={
                    'id': uuid.uuid4(),
                    'market_fee': subcat_data['market_fee']
                }
            )
            self.stdout.write(f'  {subcat_data["title"]} ({subcat_data["category"].title}): {"created" if created else "exists"}')

    def create_product_groups(self):
        """Create initial product groups"""
        self.stdout.write('Creating product groups...')
        
        # ProductGroup requires a sub_category, so we'll skip this for now
        # as we need to create subcategories first
        self.stdout.write('  Skipping product groups (requires subcategories)')
