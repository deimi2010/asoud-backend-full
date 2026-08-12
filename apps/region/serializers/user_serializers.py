from rest_framework import serializers

from apps.region.models import Country, Province, City


class CountryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            'id',
            'name',
        ]


class ProvinceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = [
            'id',
            'name',
        ]


class CityListSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = [
            'id',
            'name',
        ]
