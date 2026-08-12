from apps.base.models import models, BaseModel
from django.utils.translation import gettext_lazy as _
from apps.product.models import Product
from apps.category.models import Category
from apps.users.models import User
from apps.region.models import (
    Province,
    City
)
import os
import uuid

# Create your models here.

def upload_advertise_image(instance, filename):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    return f"img/advertise/{uuid.uuid4()}{extension}"



class AdvKeyword(BaseModel):
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Name')
    )

    class Meta:
        db_table = 'advertise_keyword'
        verbose_name = _('Keyword')
        verbose_name_plural = _('Keywords')

    def __str__(self):
        return self.name


class Advertisement(BaseModel):
    SERVICE = 'service'
    GOOD = 'good'

    TYPE_CHOICES = [
        (SERVICE, _('Service')),
        (GOOD, _('Good')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='advertises',
        verbose_name=_('User')
    )
    type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES,
        verbose_name=_('Type')
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('Name')
    )
    description = models.TextField(
        verbose_name=_('Description')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='advertisements',
        null=True,
        blank=True,
        verbose_name=_('Category')
    )
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="advertises",
        verbose_name=_('State')
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="advertises",
        verbose_name=_('City')
    )
    email = models.EmailField(
        null=True,
        blank=True,
        verbose_name=_('Email')
    )
    keywords = models.ManyToManyField(
        AdvKeyword,
        related_name='advertisements',
        blank=True,
        verbose_name=_('Keywords'),
    )
    price = models.DecimalField(
        max_digits=15, 
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('Price')
    )
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        related_name='advertisements',
        null=True, 
        blank=True,
        verbose_name=_('Product')
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name=_('Is Paid')
    )

    class Meta:
        db_table='advertisement'
        ordering = ['-created_at']
        verbose_name=_('Advertisement')
        verbose_name_plural=_('Advertisements')

    def __str__(self):
        return self.name
    

class AdvImage(BaseModel):
    advertise = models.ForeignKey(
        Advertisement,
        related_name='images',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Advertisement')
    )

    image = models.ImageField(
        upload_to=upload_advertise_image
    )

    class Meta:
        db_table='advertisement_image'
        ordering = ['-created_at']
        verbose_name=_('Advertisement Image')
        verbose_name_plural=_('Advertisement Images')

    def __str__(self):
        return str(self.id)[:4]
