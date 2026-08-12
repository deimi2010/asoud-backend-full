from rest_framework import serializers

from apps.category.models import (
    Group, Category, SubCategory,
    ProductGroup, ProductCategory, ProductSubCategory
    )


class GroupListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'id',
            'title',
        ]


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id',
            'title',
        ]


class SubCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = [
            'id',
            'title',
        ]


class SubCategoryImgSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = [
            'id',
            'title',
            'market_slider_img'
        ]

class CategoryImgSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = [
            'id',
            'title',
            'market_slider_img'
        ]

class GroupImgSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = [
            'id',
            'title',
            'market_slider_img'
        ]


class ProductGroupListSerializer(serializers.ModelSerializer):
    sub_category = serializers.SerializerMethodField()
    class Meta:
        model = ProductGroup
        fields = [
            'id',
            'sub_category',
        ]
    def get_sub_category(self, obj):
        return obj.sub_category.title



class ProductCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = [
            'id',
            'title',
        ]


class ProductSubCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSubCategory
        fields = [
            'id',
            'title',
        ]