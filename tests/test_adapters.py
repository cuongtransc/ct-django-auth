from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from ct_django_auth.adapters import invite_only_enabled
from ct_django_auth.testing import GitHubLoginMixin


class InviteOnlySettingTests(TestCase):
    @override_settings()
    def test_absent_setting_means_invite_only(self):
        from django.conf import settings

        del settings.INVITE_ONLY
        self.assertTrue(invite_only_enabled())

    @override_settings(INVITE_ONLY='False')
    def test_invite_only_string_false_stays_closed(self):
        self.assertTrue(invite_only_enabled())

    @override_settings(INVITE_ONLY=False)
    def test_boolean_false_opens_signup(self):
        self.assertFalse(invite_only_enabled())


class OpenSignupTests(GitHubLoginMixin, TestCase):
    @override_settings(INVITE_ONLY=False)
    def test_open_signup_creates_and_signs_in_user(self):
        self.github_login('newbie@example.com')
        user = get_user_model().objects.get(email='newbie@example.com')
        self.assertEqual(self.signed_in_pk(), str(user.pk))
