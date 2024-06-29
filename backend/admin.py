from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, Brand, Image


class CustomUserAdmin(UserAdmin):
    model = User
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'type', 'image')
    list_display = ('email', 'image', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')


class UserInline(admin.TabularInline):
    model = User
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'type', 'image')
    list_display = ('email', 'image', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')


@admin.register(Image)
class Images(admin.ModelAdmin):
    model = Image
    fields = ('title', 'image')
    inlines = [UserInline]


class ProductInfoInline(admin.TabularInline):
    model = ProductInfo
    fields = ['product', 'model', 'brand', 'shop', 'external_id', 'quantity', 'price', 'price_rrc', 'image']


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



admin.site.register(ProductParameter)
admin.site.register(Parameter)
admin.site.register(Contact)
admin.site.register(Brand)
admin.site.register(User)