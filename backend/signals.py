from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django_rest_passwordreset.signals import reset_password_token_created
from .models import ConfirmEmailToken, User

new_order = Signal()
new_user_registered = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
        Отправляем письмо с токеном для сброса пароля
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
        [reset_password_token.user.email])
    msg = EmailMultiAlternatives(subject, message, from_email, [to])
    msg.send()


@receiver(post_save, sender=User)
def new_user_registered_signal(sender, instance, created, **kwargs):
    """
    Создаем токен подтверждения email
    """
    if created and not instance.is_active:
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)
        msg = EmailMultiAlternatives(
            f"Confirm your email {instance.email}",
            body=token.key,
            from_email=settings.EMAIL_HOST_USER,
            to=[instance.email]
        )
        msg.send()

@receiver(new_order)
def new_order_signal(sender, **kwargs):
    """
    отправяем письмо при изменении статуса заказа
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