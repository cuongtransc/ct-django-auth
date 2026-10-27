from django.contrib.auth import get_user_model
from django.test import TestCase

from ct_django_auth.testing import OAuthContractTests


class TestProjectContract(OAuthContractTests, TestCase):
    login_redirect_url = '/home/'

    def make_invitee(self, email):
        return get_user_model().objects.create_user(username=email, email=email)
