"""
Management command to create sample data for development and testing
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.category.models import Group, Category, SubCategory, ProductGroup, ProductCategory, ProductSubCategory
from apps.region.models import Country, Province, City
from apps.users.models import User
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create sample data for the application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self.clear_data()
        
        self.stdout.write('Creating sample data...')
        
        with transaction.atomic():
            self.create_regions()
            self.create_groups()
            self.create_categories()
            self.create_subcategories()
            self.create_product_groups()
            self.create_product_categories()
            self.create_product_subcategories()
            self.create_sample_users()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )

    def clear_data(self):
        """Clear existing data"""
        ProductSubCategory.objects.all().delete()
        ProductCategory.objects.all().delete()
        ProductGroup.objects.all().delete()
        SubCategory.objects.all().delete()
        Category.objects.all().delete()
        Group.objects.all().delete()
        City.objects.all().delete()
        Province.objects.all().delete()
        Country.objects.all().delete()

    def create_regions(self):
        """Create sample regions"""
        # Create Iran
        iran, created = Country.objects.get_or_create(
            name='ایران'
        )
        
        # Create Tehran Province
        tehran_province, created = Province.objects.get_or_create(
            name='تهران',
            country=iran
        )
        
        # Create Tehran City
        tehran_city, created = City.objects.get_or_create(
            name='تهران',
            province=tehran_province
        )
        
        self.stdout.write(f'Created regions: {iran.name} -> {tehran_province.name} -> {tehran_city.name}')

    def create_groups(self):
        """Create sample groups"""
        groups_data = [
            {'title': 'غذا و رستوران', 'market_fee': Decimal('5.000')},
            {'title': 'پوشاک و مد', 'market_fee': Decimal('7.500')},
            {'title': 'الکترونیک و تکنولوژی', 'market_fee': Decimal('10.000')},
            {'title': 'خودرو و موتورسیکلت', 'market_fee': Decimal('15.000')},
            {'title': 'خانه و آشپزخانه', 'market_fee': Decimal('8.000')},
            {'title': 'ورزش و سرگرمی', 'market_fee': Decimal('6.000')},
            {'title': 'زیبایی و سلامت', 'market_fee': Decimal('12.000')},
            {'title': 'کتاب و آموزش', 'market_fee': Decimal('4.000')},
        ]
        
        for group_data in groups_data:
            group, created = Group.objects.get_or_create(
                title=group_data['title'],
                defaults={'market_fee': group_data['market_fee']}
            )
            if created:
                self.stdout.write(f'Created group: {group.title}')

    def create_categories(self):
        """Create sample categories"""
        groups = Group.objects.all()
        
        categories_data = {
            'غذا و رستوران': [
                'رستوران ایرانی', 'فست فود', 'کافه', 'شیرینی و دسر', 'غذای محلی'
            ],
            'پوشاک و مد': [
                'لباس مردانه', 'لباس زنانه', 'لباس بچه', 'کفش', 'اکسسوری'
            ],
            'الکترونیک و تکنولوژی': [
                'موبایل و تبلت', 'لپ تاپ و کامپیوتر', 'گجت و لوازم جانبی', 'کنسول بازی'
            ],
            'خودرو و موتورسیکلت': [
                'خودرو', 'موتورسیکلت', 'لوازم یدکی', 'لوازم جانبی خودرو'
            ],
            'خانه و آشپزخانه': [
                'مبلمان', 'لوازم آشپزخانه', 'دکوراسیون', 'لوازم برقی خانه'
            ],
            'ورزش و سرگرمی': [
                'ورزش', 'اسباب بازی', 'موسیقی', 'فیلم و سریال'
            ],
            'زیبایی و سلامت': [
                'لوازم آرایشی', 'عطر و ادکلن', 'لوازم بهداشتی', 'مکمل غذایی'
            ],
            'کتاب و آموزش': [
                'کتاب', 'نرم افزار آموزشی', 'دوره آنلاین', 'لوازم تحریر'
            ],
        }
        
        for group in groups:
            if group.title in categories_data:
                for category_title in categories_data[group.title]:
                    category, created = Category.objects.get_or_create(
                        title=category_title,
                        group=group,
                        defaults={'market_fee': group.market_fee * Decimal('0.5')}
                    )
                    if created:
                        self.stdout.write(f'Created category: {category.title} in {group.title}')

    def create_subcategories(self):
        """Create sample subcategories"""
        categories = Category.objects.all()
        
        subcategories_data = {
            'رستوران ایرانی': ['کباب', 'قورمه سبزی', 'قیمه', 'خورشت'],
            'فست فود': ['برگر', 'پیتزا', 'ساندویچ', 'مرغ سوخاری'],
            'لباس مردانه': ['پیراهن', 'شلوار', 'کت', 'تی شرت'],
            'لباس زنانه': ['لباس', 'شلوار', 'بلوز', 'دامن'],
            'موبایل و تبلت': ['گوشی هوشمند', 'تبلت', 'لوازم جانبی موبایل'],
        }
        
        for category in categories:
            if category.title in subcategories_data:
                for subcategory_title in subcategories_data[category.title]:
                    subcategory, created = SubCategory.objects.get_or_create(
                        title=subcategory_title,
                        category=category,
                        defaults={'market_fee': category.market_fee * Decimal('0.3')}
                    )
                    if created:
                        self.stdout.write(f'Created subcategory: {subcategory.title} in {category.title}')

    def create_product_groups(self):
        """Create sample product groups"""
        # Get some subcategories to create product groups
        subcategories = SubCategory.objects.all()[:5]  # Take first 5 subcategories
        
        for subcategory in subcategories:
            group, created = ProductGroup.objects.get_or_create(
                sub_category=subcategory
            )
            if created:
                self.stdout.write(f'Created product group: {group.sub_category.title}')

    def create_product_categories(self):
        """Create sample product categories"""
        product_groups = ProductGroup.objects.all()
        
        # Create some sample product categories for each product group
        for group in product_groups:
            # Create 2-3 categories for each product group
            for i in range(2):
                category_title = f"{group.sub_category.title} - دسته {i+1}"
                category, created = ProductCategory.objects.get_or_create(
                    title=category_title,
                    product_group=group
                )
                if created:
                    self.stdout.write(f'Created product category: {category.title} in {group.sub_category.title}')

    def create_product_subcategories(self):
        """Create sample product subcategories"""
        product_categories = ProductCategory.objects.all()
        
        # Create some sample product subcategories for each product category
        for category in product_categories:
            # Create 1-2 subcategories for each product category
            for i in range(2):
                subcategory_title = f"{category.title} - زیردسته {i+1}"
                subcategory, created = ProductSubCategory.objects.get_or_create(
                    title=subcategory_title,
                    product_category=category
                )
                if created:
                    self.stdout.write(f'Created product subcategory: {subcategory.title} in {category.title}')

    def create_sample_users(self):
        """Create sample users"""
        users_data = [
            {'mobile_number': '09123456789', 'first_name': 'مدیر', 'last_name': 'سیستم', 'type': 'owner'},
            {'mobile_number': '09987654321', 'first_name': 'کاربر', 'last_name': 'تست', 'type': 'user'},
        ]
        
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                mobile_number=user_data['mobile_number'],
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'type': user_data['type'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created user: {user.mobile_number}')
