from django.contrib.auth import get_user_model
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django_rest_passwordreset.signals import reset_password_token_created

from djangoProjectFinalWork.tasks import register_confirm_email, send_order_email, password_reset_email_task
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
    token = ConfirmEmailToken(user=reset_password_token.user, key=reset_password_token.key)
    if token:
        password_reset_email_task.delay(token.user_id, token.key, token.user.email)


@receiver(post_save, sender=get_user_model())
def new_user_registered_signal(sender, instance, created, **kwargs):
    """
    If a new user is registered, send an e-mail to confirm the email address.
        """
    if created and not instance.is_active:
        # this task will be executed in celery
        register_confirm_email.delay(instance.pk)


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Sending an e-mail to the user when a new order is created
        """
    # send an e-mail to the user
    user = User.objects.get(id=user_id)
    if user:
        # this task will be executed in celery
        send_order_email.delay(user.pk)
