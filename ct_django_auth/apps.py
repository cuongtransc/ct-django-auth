from django.apps import AppConfig


class CtDjangoAuthConfig(AppConfig):
    name = 'ct_django_auth'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import checks  # noqa: F401  (registers the system checks)
