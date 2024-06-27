from django.apps import AppConfig


class CustomConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        from backend.signals import new_user_registered,new_user_registered_signal
        new_user_registered.connect(new_user_registered_signal)

