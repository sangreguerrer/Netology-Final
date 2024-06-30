from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, Brand, Image


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'type',)


class BrandAdmin(admin.ModelAdmin):
    model = Brand
    fields = ("name", "country", "email", "url", "image")


class ProductInfoAdmin(admin.ModelAdmin):
    model = ProductInfo
    fields = ['product', 'model', 'brand', 'shop', 'external_id', 'quantity', 'price', 'price_rrc', 'image']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    model = Product
    list_display = ('name', 'category')


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

admin.site.register(ProductParameter)
admin.site.register(Parameter)
admin.site.register(Contact)
admin.site.register(Brand)
