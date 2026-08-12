from apps.base.admin import admin, BaseAdmin, BaseTabularInline

from .models import(
    Group, Category, SubCategory,
    ProductGroup, ProductCategory, ProductSubCategory
    )

# Register your models here.


class SubCategoryTabularInline(BaseTabularInline):
    model = SubCategory

    fields = (
        'title',
        'market_fee',
        'market_slider_img',
        'market_slider_url',
    )


class CategoryAdmin(BaseAdmin):
    inlines = [
        SubCategoryTabularInline,
    ]

    list_display = [
        'title',
        'group',
    ]

    fields = (
        'group',
        'title',
        'market_fee',
        'market_slider_img',
        'market_slider_url',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(Category, CategoryAdmin)


class GroupAdmin(BaseAdmin):
    list_display = [
        'title',
    ]

    fields = (
        'title', 'market_fee', 'market_slider_img', 'market_slider_url'
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(Group, GroupAdmin)


class ProductGroupAdmin(BaseAdmin):
    list_display = [
        # 'title',
        'sub_category'
    ]

    fields = (
     'sub_category', 
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


class ProductSubCategoryTabularInline(BaseTabularInline):
    model = ProductSubCategory

    fields = (
        'title',
    )

class ProductCategoryAdmin(BaseAdmin):
    inlines = [
        ProductSubCategoryTabularInline,
    ]

    list_display = [
        'title',
        'product_group',
    ]
    fields = (
        'product_group',
        'title',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields

admin.site.register(ProductCategory, ProductCategoryAdmin)
admin.site.register(ProductGroup, ProductGroupAdmin)
