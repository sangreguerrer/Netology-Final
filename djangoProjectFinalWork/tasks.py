import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver

import celery
from backend.models import ConfirmEmailToken, User
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
