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
from baton.autodiscover import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from backend.admin_features import admin_search
from backend.views import (RegisterView, confirm_acc, AccountDetails, login, partner_update,
                           ShopView, BrandView, product_view, PartnerState, BasketView, OrdersView, ContactView,
                           PartnerOrders, image_upload_view, login_page, ErrorTriggerView, )
app_name = 'backend'
# handler404 = 'backend.views.my_custom_page_not_found_view'
# handler403 = 'backend.views.my_custom_permission_denied_view'
# handler500 = 'backend.views.my_custom_server_error_view'

urlpatterns = [
    path('sentry-debug/', ErrorTriggerView.as_view()),
    path('admin', admin.site.urls),
    path('api/search/', admin_search),
    path('baton/', include('baton.urls')),
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
    path('user/login/choice', login_page),
    path('schema', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('upload/', image_upload_view),
    path('auth/', include('social_django.urls', namespace='social')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
