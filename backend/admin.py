from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from psycopg2 import IntegrityError
from rest_framework.exceptions import ValidationError

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, Brand, Image


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'type',)


class BrandAdmin(admin.ModelAdmin):
    model = Brand
    fields = ("name", "country", "email", "url", "image")


class ProdParInline(admin.TabularInline):
    model = ProductParameter


class ProductInfoInline(admin.TabularInline):
    model = ProductInfo
    fields = ['product', 'model', 'brand', 'shop', 'external_id', 'quantity', 'price', 'price_rrc', 'image']
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
    fields = ["user", "name", "address", "state", "image"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    model = Order
    fields = ["user", "contact", "state"]
    readonly_fields = ("created",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    model = OrderItem
    fields = ["order", "product_info", "quantity"]

    def save_model(self, request, obj, form, change):
        try:
            obj.save()
        except IntegrityError as e:
            raise ValidationError(e)


admin.site.register(ProductParameter)
admin.site.register(ProductInfo)
admin.site.register(Contact)
admin.site.register(Brand)
