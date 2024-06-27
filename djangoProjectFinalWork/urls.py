"""
URL configuration for goodplace project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from backend.import_products import ShopUpdate
from backend.views import image_upload_view, RegisterView, confirm_acc, AccountDetails, login, partner_update, ShopView, \
    BrandView

app_name = 'backend'
urlpatterns = [
    path('admin/', admin.site.urls),
    path('partner/update', partner_update, name='partner-update'),
    path('upload/', image_upload_view),
    path('shop/update', ShopUpdate.as_view(), name='shop-update'),
    path('register/', RegisterView.as_view(), name='user-register'),
    path('register/confirm/', confirm_acc, name='user-register-confirm'),
    path('register/upload/', image_upload_view),
    path('profile/', AccountDetails.as_view(), name='profile-settings'),
    path('brand/', BrandView.as_view(), name='brands'),
    path('shops', ShopView.as_view(), name='shops'),
    path('user/login/', login, name='user-login'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)