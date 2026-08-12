from django.utils.translation import gettext_lazy as _

from apps.base.models import models, BaseModel

# Create your models here.


class Country(BaseModel):
    name = models.CharField(
        max_length=255,
        verbose_name=_('Name'),
    )

    class Meta:
        db_table = 'country'
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')

    def __str__(self):
        return self.name


class Province(BaseModel):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        verbose_name=_('Country'),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('Name'),
    )

    class Meta:
        db_table = 'province'
        verbose_name = _('Province')
        verbose_name_plural = _('Provinces')

    def __str__(self):
        return self.name


class City(BaseModel):
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        verbose_name=_('Province'),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('Name'),
    )

    class Meta:
        db_table = 'city'
        verbose_name = _('City')
        verbose_name_plural = _('Cities')

    def __str__(self):
        return self.name
