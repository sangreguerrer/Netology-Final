"""
URL configuration for goodplace project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views. home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls')
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from backend.views import (RegisterView, confirm_acc, AccountDetails, login, partner_update,
                           ShopView, BrandView, product_view, PartnerState, BasketView, OrdersView, ContactView,
                           PartnerOrders)

app_name = 'backend'
urlpatterns = [
    path('admin', admin.site.urls),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('partner/update', partner_update, name='partner-update'),
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    path('register', RegisterView.as_view(), name='user-register'),
    path('register/confirm', confirm_acc, name='user-register-confirm'),
    path('user/reset_password', reset_password_request_token, name='reset_password'),
    path('user/reset_password/confirm', reset_password_confirm, name='password-reset-confirm'),
    path('contact', ContactView.as_view(), name='contact'),
    path('profile', AccountDetails.as_view(), name='profile-settings'),
    path('brand', BrandView.as_view(), name='brands'),
    path('shops', ShopView.as_view(), name='shops'),
    path('products', product_view, name='shops'),
    path('basket', BasketView.as_view(), name='basket'),
    path('order', OrdersView.as_view(), name='order'),
    path('user/login', login, name='user-login'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
