from django.urls import path, include
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


from backend.views import (RegisterView, confirm_acc, AccountDetails, login, partner_update,
    ShopView, BrandView, product_view, PartnerState, BasketView, OrdersView, ContactView,
    PartnerOrders, image_upload_view, login_page, CategoryView, )



app_name = 'backend'


urlpatterns = [
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
    path('categories', CategoryView.as_view(), name='categories'),
    path('products', product_view, name='shops'),
    path('basket', BasketView.as_view(), name='basket'),
    path('order', OrdersView.as_view(), name='order'),
    path('user/login', login, name='user-login'),
    path('user/login/choice', login_page),
    path('schema', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('image_upload', image_upload_view, name='image_upload'),
]