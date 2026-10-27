from django.conf import settings
from django.core.checks import Error, Warning, register
from django.urls import Resolver404, resolve
from django.utils.module_loading import import_string

from .adapters import InviteOnlyAccountAdapter, InviteOnlySocialAccountAdapter
from .views import admin_login

ADAPTERS = (
    ('ACCOUNT_ADAPTER', InviteOnlyAccountAdapter),
    ('SOCIALACCOUNT_ADAPTER', InviteOnlySocialAccountAdapter),
)
EMAIL_SETTINGS = (
    'SOCIALACCOUNT_QUERY_EMAIL',
    'SOCIALACCOUNT_EMAIL_AUTHENTICATION',
    'SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT',
)
NO_EMAIL_PROVIDERS = {'twitter', 'twitter_oauth2'}


@register()
def check_sign_in_policy(app_configs, **kwargs):
    errors = []

    if getattr(settings, 'SOCIALACCOUNT_LOGIN_ON_GET', False):
        errors.append(
            Error(
                'SOCIALACCOUNT_LOGIN_ON_GET must be False: a plain link would '
                'start an OAuth sign-in (login CSRF).',
                hint='Remove the setting; sign-in buttons POST with {% csrf_token %}.',
                id='ct_auth.E001',
            )
        )

    for name, expected in ADAPTERS:
        try:
            cls = import_string(getattr(settings, name, ''))
            ok = isinstance(cls, type) and issubclass(cls, expected)
        except ImportError:
            ok = False
        if not ok:
            errors.append(
                Error(
                    f'{name} must be ct_django_auth.adapters.{expected.__name__} '
                    'or a subclass of it.',
                    hint=f"Set {name} = 'ct_django_auth.adapters.{expected.__name__}'.",
                    id='ct_auth.E002',
                )
            )

    for name in EMAIL_SETTINGS:
        if getattr(settings, name, None) is not True:
            errors.append(
                Error(
                    f"{name} must be True for invites to match the provider's "
                    'verified email.',
                    hint=f'Set {name} = True.',
                    id='ct_auth.E003',
                )
            )

    if getattr(settings, 'SOCIALACCOUNT_ONLY', False) is not True:
        errors.append(
            Error(
                "SOCIALACCOUNT_ONLY must be True: allauth's password, code and "
                'reset sign-in would bypass OAuth.',
                hint='Set SOCIALACCOUNT_ONLY = True.',
                id='ct_auth.E005',
            )
        )

    try:
        routed = resolve('/admin/login/').func is admin_login
    except Resolver404:
        routed = False
    if not routed:
        errors.append(
            Error(
                '/admin/login/ must resolve to ct_django_auth.views.admin_login.',
                hint='Include ct_django_auth.urls before admin.site.urls in the '
                'root URLconf.',
                id='ct_auth.E004',
            )
        )

    for app in settings.INSTALLED_APPS:
        prefix, _, provider = app.rpartition('.')
        if prefix == 'allauth.socialaccount.providers' and (
            provider in NO_EMAIL_PROVIDERS
        ):
            errors.append(
                Warning(
                    f"Provider '{provider}' returns no email: a new user signing "
                    'in through it can never match an invite.',
                    hint='Invite such users by linking their account in the admin, '
                    'or remove the provider.',
                    id='ct_auth.W001',
                )
            )

    return errors
