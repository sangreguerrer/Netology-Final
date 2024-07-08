from django.contrib.auth import get_user_model
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django_rest_passwordreset.signals import reset_password_token_created

from djangoProjectFinalWork.tasks import register_confirm_email
from .models import ConfirmEmailToken, User

new_order = Signal()
new_user_registered = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
        Sending an e-mail to the user when a password reset token is created
        When a token is created, an e-mail needs to be sent to the user
        :param sender: View Class that sent the signal
        :param instance: View Instance that sent the signal
        :param reset_password_token: Token Model Object
        :param kwargs:
        :return:
    """
    subject, message, from_email, to = (
        f"Reset password token for: {reset_password_token.user}",
        reset_password_token.key,
        settings.EMAIL_HOST_USER,
        reset_password_token.user.email)
    msg = EmailMultiAlternatives(subject, message, from_email, [to])
    msg.send()


@receiver(post_save, sender=get_user_model())
def new_user_registered_signal(sender, instance, created, **kwargs):
    """
    If a new user is registered, send an e-mail to confirm the email address.
        """
    if created and not instance.is_active:
        register_confirm_email.delay(instance.pk)#this task will be executed in celery


@receiver(new_order)
def new_order_signal(sender, **kwargs):
    """
    Sending an e-mail to the user when a new order is created
        """
    # send an e-mail to the user
    user = User.objects.get(id=sender)

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
