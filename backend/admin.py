from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from psycopg2 import IntegrityError
from rest_framework.exceptions import ValidationError

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, Brand, Image


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('image', 'title')
    fields = ('image', 'title')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'email', 'type', 'is_staff', 'is_superuser', 'is_active', 'image_tag')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'type')

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('image',)}),
    )

    # def __init__(self, model, admin_site):
    #     super().__init__(model, admin_site)
    #     self.image = None

    @admin.display(description='Profile Image')
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="30" height="30" />'.format(obj.image.image.url))
        return 'Нет изображения'
    image_tag.short_description = 'Изображение'


class BrandAdmin(admin.ModelAdmin):
    model = Brand
    list_display = ('name', 'country', 'email', 'url', 'image')
    fields = ("name", "country", "email", "url", "image")


class ProdParInline(admin.TabularInline):
    model = ProductParameter


class ProductInfoInline(admin.TabularInline):
    model = ProductInfo
    list_display = ('product', 'model', 'quantity', 'price', 'price_rrc')
    inlines = [ProdParInline]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    model = Parameter
    inlines = [ProdParInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    model = Product
    list_display = ('name', 'category')
    inlines = [ProductInfoInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    model = Category
    fields = ("name", "shops")


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    model = Shop
    list_filter = ('state', 'user')
    fields = ["user", "name", "address", "state", "image"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    model = Order
    fields = ["user", "contact", "state"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    model = OrderItem
    fields = ["order", "product_info", "quantity"]

    def save_model(self, request, obj, form, change):
        try:
            obj.save()
        except IntegrityError as e:
            raise ValidationError(e)


# admin.site.register(Image)
admin.site.register(ProductParameter)
admin.site.register(ProductInfo)
admin.site.register(Contact)
admin.site.register(Brand)
