from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, Brand, Image


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'type', 'image')
    list_display = ('email', 'image', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')


class UserInline(admin.StackedInline):
    model = User
    fk_name = 'image'

@admin.register(Image)
class Images(admin.ModelAdmin):
    model = Image
    fields = ('title', 'image')
    inlines = [UserInline]






@admin.register(Category)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    model = Shop
    fields = ["user", "name", "address", "state", "image"]



