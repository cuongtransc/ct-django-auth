from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from ct_django_auth.testing import OAuthContractTests


class TestProjectContract(OAuthContractTests, TestCase):
    login_redirect_url = '/home/'

    def make_invitee(self, email):
        return get_user_model().objects.create_user(username=email, email=email)


@override_settings(LOGIN_URL='/home/')
class CustomLoginUrlContract(OAuthContractTests, TestCase):
    """An app whose LOGIN_URL is not allauth's page; its dead-end pages (the
    package's here) still link allauth's, so it sets sign_in_url."""

    login_redirect_url = '/home/'
    sign_in_url = '/accounts/login/'

    def make_invitee(self, email):
        return get_user_model().objects.create_user(username=email, email=email)


@override_settings(ROOT_URLCONF='tests.urls_reset_redirect')
class ResetRedirectContract(OAuthContractTests, TestCase):
    """An app that redirects /accounts/password/reset/ instead of serving 404."""

    login_redirect_url = '/home/'

    def make_invitee(self, email):
        return get_user_model().objects.create_user(username=email, email=email)
