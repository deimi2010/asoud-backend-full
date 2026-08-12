import uuid
from django.core.management.base import BaseCommand
from apps.category.models import Group, Category, SubCategory

class Command(BaseCommand):
    help = 'Complete all groups with categories and subcategories'

    def handle(self, *args, **options):
        self.stdout.write('Starting to complete all groups...')
        
        # Complete all groups
        self.complete_food_group()
        self.complete_clothing_group()
        self.complete_electronics_group()
        self.complete_automotive_group()
        self.complete_home_group()
        self.complete_sports_group()
        self.complete_beauty_group()
        self.complete_books_group()
        
        # Complete missing subcategories
        self.complete_missing_subcategories()

        self.stdout.write(
            self.style.SUCCESS('Successfully completed all groups!')
        )

    def complete_food_group(self):
        """Complete food and restaurant group"""
        self.stdout.write('Completing food group...')
        
        food_group = Group.objects.get(title='غذا و رستوران')
        
        # Add missing subcategories for existing categories
        categories_to_complete = [
            ('سوپرمارکت', [
                {'title': 'مواد غذایی', 'market_fee': 2.000},
                {'title': 'نوشیدنی', 'market_fee': 2.500},
                {'title': 'شیرینی و شکلات', 'market_fee': 3.000},
                {'title': 'میوه و سبزیجات', 'market_fee': 1.500},
            ])
        ]
        
        for cat_title, subcats in categories_to_complete:
            try:
                category = Category.objects.get(title=cat_title, group=food_group)
                for subcat_data in subcats:
                    subcategory, created = SubCategory.objects.get_or_create(
                        title=subcat_data['title'],
                        category=category,
                        defaults={'market_fee': subcat_data['market_fee']}
                    )
                    self.stdout.write(f'  {subcat_data["title"]}: {"created" if created else "exists"}')
            except Category.DoesNotExist:
                self.stdout.write(f'  Category {cat_title} not found')

    def complete_clothing_group(self):
        """Complete clothing group"""
        self.stdout.write('Completing clothing group...')
        
        clothing_group = Group.objects.get(title='پوشاک و مد')
        
        # Complete missing subcategories
        categories_to_complete = [
            ('لباس بچه', [
                {'title': 'لباس نوزاد', 'market_fee': 2.000},
                {'title': 'لباس کودک', 'market_fee': 2.500},
                {'title': 'لباس نوجوان', 'market_fee': 3.000},
            ]),
            ('کفش', [
                {'title': 'کفش ورزشی', 'market_fee': 3.500},
                {'title': 'کفش رسمی', 'market_fee': 4.000},
                {'title': 'کفش راحتی', 'market_fee': 3.000},
            ]),
            ('اکسسوری', [
                {'title': 'ساعت', 'market_fee': 2.500},
                {'title': 'کیف', 'market_fee': 3.000},
                {'title': 'کمربند', 'market_fee': 2.000},
            ])
        ]
        
        for cat_title, subcats in categories_to_complete:
            try:
                category = Category.objects.get(title=cat_title, group=clothing_group)
                for subcat_data in subcats:
                    subcategory, created = SubCategory.objects.get_or_create(
                        title=subcat_data['title'],
                        category=category,
                        defaults={'market_fee': subcat_data['market_fee']}
                    )
                    self.stdout.write(f'  {subcat_data["title"]}: {"created" if created else "exists"}')
            except Category.DoesNotExist:
                self.stdout.write(f'  Category {cat_title} not found')

    def complete_electronics_group(self):
        """Complete electronics group"""
        self.stdout.write('Completing electronics group...')
        
        electronics_group = Group.objects.get(title='الکترونیک و دیجیتال')
        
        # Complete missing subcategories
        categories_to_complete = [
            ('لپ تاپ و کامپیوتر', [
                {'title': 'لپ تاپ', 'market_fee': 1.500},
                {'title': 'کامپیوتر رومیزی', 'market_fee': 1.800},
                {'title': 'مانیتور', 'market_fee': 1.200},
            ]),
            ('لوازم جانبی', [
                {'title': 'کیبورد و ماوس', 'market_fee': 0.800},
                {'title': 'اسپیکر', 'market_fee': 1.000},
                {'title': 'هارد اکسترنال', 'market_fee': 1.200},
            ]),
            ('گیم و سرگرمی', [
                {'title': 'کنسول بازی', 'market_fee': 2.000},
                {'title': 'بازی کامپیوتری', 'market_fee': 1.500},
                {'title': 'کنترلر', 'market_fee': 1.000},
            ])
        ]
        
        for cat_title, subcats in categories_to_complete:
            try:
                category = Category.objects.get(title=cat_title, group=electronics_group)
                for subcat_data in subcats:
                    subcategory, created = SubCategory.objects.get_or_create(
                        title=subcat_data['title'],
                        category=category,
                        defaults={'market_fee': subcat_data['market_fee']}
                    )
                    self.stdout.write(f'  {subcat_data["title"]}: {"created" if created else "exists"}')
            except Category.DoesNotExist:
                self.stdout.write(f'  Category {cat_title} not found')

    def complete_automotive_group(self):
        """Complete automotive group"""
        self.stdout.write('Completing automotive group...')
        
        automotive_group = Group.objects.get(title='خودرو و موتورسیکلت')
        
        # Create categories
        categories_data = [
            {'title': 'خودرو', 'market_fee': 1.000},
            {'title': 'موتورسیکلت', 'market_fee': 1.200},
            {'title': 'لوازم یدکی', 'market_fee': 0.800},
            {'title': 'لوازم جانبی خودرو', 'market_fee': 0.600},
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                title=cat_data['title'],
                group=automotive_group,
                defaults={'market_fee': cat_data['market_fee']}
            )
            self.stdout.write(f'  {cat_data["title"]}: {"created" if created else "exists"}')
            
            # Create subcategories
            subcategories_data = [
                {'title': f'{cat_data["title"]} نو', 'market_fee': cat_data['market_fee'] + 0.3},
                {'title': f'{cat_data["title"]} دست دوم', 'market_fee': cat_data['market_fee'] - 0.2},
                {'title': f'{cat_data["title"]} لوکس', 'market_fee': cat_data['market_fee'] + 0.5},
            ]
            
            for subcat_data in subcategories_data:
                subcategory, created = SubCategory.objects.get_or_create(
                    title=subcat_data['title'],
                    category=category,
                    defaults={'market_fee': subcat_data['market_fee']}
                )
                self.stdout.write(f'    {subcat_data["title"]}: {"created" if created else "exists"}')

    def complete_home_group(self):
        """Complete home group"""
        self.stdout.write('Completing home group...')
        
        home_group = Group.objects.get(title='خانه و آشپزخانه')
        
        # Complete missing subcategories
        categories_to_complete = [
            ('مبلمان', [
                {'title': 'مبلمان نشیمن', 'market_fee': 2.500},
                {'title': 'مبلمان خواب', 'market_fee': 3.000},
                {'title': 'مبلمان اداری', 'market_fee': 2.800},
            ]),
            ('دکوراسیون', [
                {'title': 'تابلو', 'market_fee': 1.500},
                {'title': 'گلدان', 'market_fee': 1.000},
                {'title': 'آینه', 'market_fee': 1.200},
            ]),
            ('لوازم آشپزخانه', [
                {'title': 'ظروف', 'market_fee': 1.800},
                {'title': 'لوازم پخت', 'market_fee': 2.000},
                {'title': 'لوازم برقی', 'market_fee': 1.500},
            ]),
            ('نور و روشنایی', [
                {'title': 'چراغ سقفی', 'market_fee': 1.200},
                {'title': 'چراغ رومیزی', 'market_fee': 1.000},
                {'title': 'چراغ دیواری', 'market_fee': 1.100},
            ])
        ]
        
        for cat_title, subcats in categories_to_complete:
            try:
                category = Category.objects.get(title=cat_title, group=home_group)
                for subcat_data in subcats:
                    subcategory, created = SubCategory.objects.get_or_create(
                        title=subcat_data['title'],
                        category=category,
                        defaults={'market_fee': subcat_data['market_fee']}
                    )
                    self.stdout.write(f'  {subcat_data["title"]}: {"created" if created else "exists"}')
            except Category.DoesNotExist:
                self.stdout.write(f'  Category {cat_title} not found')

    def complete_sports_group(self):
        """Complete sports group"""
        self.stdout.write('Completing sports group...')
        
        sports_group = Group.objects.get(title='ورزش و تفریح')
        
        # Create categories
        categories_data = [
            {'title': 'ورزش', 'market_fee': 2.000},
            {'title': 'تفریح', 'market_fee': 1.500},
            {'title': 'سفر', 'market_fee': 3.000},
            {'title': 'لوازم ورزشی', 'market_fee': 1.800},
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                title=cat_data['title'],
                group=sports_group,
                defaults={'market_fee': cat_data['market_fee']}
            )
            self.stdout.write(f'  {cat_data["title"]}: {"created" if created else "exists"}')
            
            # Create subcategories
            subcategories_data = [
                {'title': f'{cat_data["title"]} حرفه‌ای', 'market_fee': cat_data['market_fee'] + 0.5},
                {'title': f'{cat_data["title"]} آماتور', 'market_fee': cat_data['market_fee'] - 0.3},
                {'title': f'{cat_data["title"]} مبتدی', 'market_fee': cat_data['market_fee'] - 0.5},
            ]
            
            for subcat_data in subcategories_data:
                subcategory, created = SubCategory.objects.get_or_create(
                    title=subcat_data['title'],
                    category=category,
                    defaults={'market_fee': subcat_data['market_fee']}
                )
                self.stdout.write(f'    {subcat_data["title"]}: {"created" if created else "exists"}')

    def complete_beauty_group(self):
        """Complete beauty group"""
        self.stdout.write('Completing beauty group...')
        
        beauty_group = Group.objects.get(title='زیبایی و سلامت')
        
        # Create categories
        categories_data = [
            {'title': 'زیبایی', 'market_fee': 2.500},
            {'title': 'سلامت', 'market_fee': 2.000},
            {'title': 'عطر و ادکلن', 'market_fee': 3.000},
            {'title': 'لوازم آرایش', 'market_fee': 2.800},
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                title=cat_data['title'],
                group=beauty_group,
                defaults={'market_fee': cat_data['market_fee']}
            )
            self.stdout.write(f'  {cat_data["title"]}: {"created" if created else "exists"}')
            
            # Create subcategories
            subcategories_data = [
                {'title': f'{cat_data["title"]} برند معتبر', 'market_fee': cat_data['market_fee'] + 0.5},
                {'title': f'{cat_data["title"]} ارزان', 'market_fee': cat_data['market_fee'] - 0.5},
                {'title': f'{cat_data["title"]} طبیعی', 'market_fee': cat_data['market_fee'] + 0.3},
            ]
            
            for subcat_data in subcategories_data:
                subcategory, created = SubCategory.objects.get_or_create(
                    title=subcat_data['title'],
                    category=category,
                    defaults={'market_fee': subcat_data['market_fee']}
                )
                self.stdout.write(f'    {subcat_data["title"]}: {"created" if created else "exists"}')

    def complete_books_group(self):
        """Complete books group"""
        self.stdout.write('Completing books group...')
        
        books_group = Group.objects.get(title='کتاب و لوازم تحریر')
        
        # Create categories
        categories_data = [
            {'title': 'کتاب', 'market_fee': 1.000},
            {'title': 'لوازم تحریر', 'market_fee': 1.200},
            {'title': 'کتاب‌های درسی', 'market_fee': 0.800},
            {'title': 'مجله', 'market_fee': 0.600},
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                title=cat_data['title'],
                group=books_group,
                defaults={'market_fee': cat_data['market_fee']}
            )
            self.stdout.write(f'  {cat_data["title"]}: {"created" if created else "exists"}')
            
            # Create subcategories
            subcategories_data = [
                {'title': f'{cat_data["title"]} نو', 'market_fee': cat_data['market_fee'] + 0.2},
                {'title': f'{cat_data["title"]} دست دوم', 'market_fee': cat_data['market_fee'] - 0.3},
                {'title': f'{cat_data["title"]} کلاسیک', 'market_fee': cat_data['market_fee'] + 0.1},
            ]
            
            for subcat_data in subcategories_data:
                subcategory, created = SubCategory.objects.get_or_create(
                    title=subcat_data['title'],
                    category=category,
                    defaults={'market_fee': subcat_data['market_fee']}
                )
                self.stdout.write(f'    {subcat_data["title"]}: {"created" if created else "exists"}')

    def complete_missing_subcategories(self):
        """Complete missing subcategories for existing categories"""
        self.stdout.write('Completing missing subcategories...')
        
        # Find categories without subcategories
        categories_without_subcats = []
        for category in Category.objects.all():
            subcat_count = SubCategory.objects.filter(category=category).count()
            if subcat_count == 0:
                categories_without_subcats.append(category)
        
        for category in categories_without_subcats:
            self.stdout.write(f'  Adding subcategories for {category.title}...')
            
            # Create 3 default subcategories
            subcategories_data = [
                {'title': f'{category.title} برند A', 'market_fee': category.market_fee + 0.3},
                {'title': f'{category.title} برند B', 'market_fee': category.market_fee + 0.1},
                {'title': f'{category.title} ارزان', 'market_fee': category.market_fee - 0.2},
            ]
            
            for subcat_data in subcategories_data:
                subcategory, created = SubCategory.objects.get_or_create(
                    title=subcat_data['title'],
                    category=category,
                    defaults={'market_fee': subcat_data['market_fee']}
                )
                self.stdout.write(f'    {subcat_data["title"]}: {"created" if created else "exists"}')

