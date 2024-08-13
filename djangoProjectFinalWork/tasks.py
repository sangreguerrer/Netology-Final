import logging

import yaml
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.core.validators import URLValidator

import celery
from django.http import HttpResponse
from requests import get
from rest_framework.exceptions import ValidationError
from yaml import safe_load

from backend.models import ConfirmEmailToken, Shop, Category, ProductInfo, Brand, Product, Parameter, \
    ProductParameter
from djangoProjectFinalWork import settings

app = celery.Celery(
    'tasks',
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/1',
    broker_connection_retry_on_startup=True
)


@shared_task
def register_confirm_email(user_id):
    """
       Создаем токен подтверждения email
    """
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.pk)
        msg = EmailMultiAlternatives(
            f"Confirm your email {user.email}",
            body=token.key,
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email]
        )
        msg.send()
    except user_model.DoesNotExist:
        logging.warning("Tried to send verification email to non-existing user '%s'" % user_id)


@shared_task
def password_reset_email_task(user, token, email):
    """
       Sending an e-mail to the user when a password reset token is created
       When a token is created, an e-mail needs to be sent to the user
       :param sender: View Class that sent the signal
       :param instance: View Instance that sent the signal
       :param kwargs:
       :return:
    """
    subject, message, from_email, to = (
        f"Reset password token for: {user}",
        token, settings.EMAIL_HOST_USER, email)
    msg = EmailMultiAlternatives(subject, message, from_email, [to])
    msg.send()


@shared_task
def send_order_email(user_id):
    """
    Sending an e-mail to the user when a new order is created
    """
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
        # send an e-mail to the user
        msg = EmailMultiAlternatives(
            # title:
            f"Обновление статуса заказа",
            # message:
            'Заказ сформирован',
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [user.email]
        )
        msg.send()
    except user_model.DoesNotExist:
        logging.warning("Tried to send verification email to non-existing user '%s'" % user_id)


@shared_task
def do_import(user_id, url):
    """
    Импортируем данные из yaml файла
    """
    user_model = get_user_model()
    user = user_model.objects.get(pk=user_id)
    try:
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as err:
            return f'Status: False, Error: {str(err)}',
        else:
            try:
                stream = get(url).content
                yaml_file = safe_load(stream)
            except yaml.YAMLError as exc:
                return HttpResponse(f'Status: False, Error: YAML Error: {exc}')
            shop, _ = Shop.objects.get_or_create(name=yaml_file['shop'], user_id=user.pk)
            for category in yaml_file['categories']:
                category_obj, _ = Category.objects.get_or_create(name=category['name'])
                category_obj.shops.add(shop.id)
                category_obj.save()
            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for product in yaml_file['goods']:
                product_obj, _ = Product.objects.get_or_create(name=product['name'], category=category_obj)
                if product['brand']:
                    brand, _ = Brand.objects.get_or_create(name=product.get('brand'))
                    brand_name = Brand.objects.filter(name=product.get('brand')).first()
                product_info = ProductInfo.objects.create(
                    product_id=product_obj.id,
                    external_id=product['id'],
                    model=product['model'],
                    price=product['price'],
                    price_rrc=product['price_rrc'],
                    quantity=product['quantity'],
                    shop_id=shop.id,
                    brand=brand_name,
                )
                product_info.save()
                print(product_info)
                for name, value in product['parameters'].items():
                    parameter_obj, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(
                        product_info_id=product_info.id,
                        parameter_id=parameter_obj.id,
                        value=value,
                    )

    except user_model.DoesNotExist:
        return 'Status: False, Error: User does not exist'
    finally:
        return 'Status: True'
