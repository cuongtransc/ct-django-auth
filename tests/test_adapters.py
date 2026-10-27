from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from ct_django_auth.adapters import InviteOnlySocialAccountAdapter, invite_only_enabled
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


class FakeLogin:
    def __init__(self, *addresses):
        self.email_addresses = [
            EmailAddress(email=email, verified=verified)
            for email, verified in addresses
        ]


class AlwaysByEmail(InviteOnlySocialAccountAdapter):
    def can_authenticate_by_email(self, login, email):
        return True


class PostgresFolding(AlwaysByEmail):
    """Return candidates the way Postgres UPPER() folds them: 'ı' and 'ſ'
    upper-case to ASCII, so a lookalike address reaches the Python filter."""

    def invite_candidates(self, email):
        for user in get_user_model().objects.all():
            if user.email.upper() == email.upper():
                yield user, user.email


class InviteMatchTests(TestCase):
    def make_user(self, email):
        return get_user_model().objects.create_user(username=email, email=email)

    def test_dotless_i_lookalike_is_refused(self):
        self.make_user('kırk@example.com')
        login = FakeLogin(('kirk@example.com', True))
        self.assertIsNone(PostgresFolding().authenticate_by_email(login))

    def test_long_s_lookalike_is_refused(self):
        self.make_user('ſam@example.com')
        login = FakeLogin(('SAM@example.com', True))
        self.assertIsNone(PostgresFolding().authenticate_by_email(login))

    def test_case_only_difference_still_matches(self):
        user = self.make_user('Kirk@Example.com')
        login = FakeLogin(('kirk@example.com', True))
        self.assertEqual(
            PostgresFolding().authenticate_by_email(login),
            (user, 'kirk@example.com'),
        )

    def test_user_with_own_verified_row_counts_once(self):
        user = self.make_user('gina@example.com')
        EmailAddress.objects.create(user=user, email='gina@example.com', verified=True)
        login = FakeLogin(('gina@example.com', True))
        self.assertEqual(
            AlwaysByEmail().authenticate_by_email(login), (user, 'gina@example.com')
        )

    def test_addresses_matching_different_users_are_refused(self):
        self.make_user('hal@example.com')
        self.make_user('ida@example.com')
        login = FakeLogin(('hal@example.com', True), ('ida@example.com', True))
        self.assertIsNone(AlwaysByEmail().authenticate_by_email(login))

    def test_unverified_provider_address_is_ignored(self):
        self.make_user('jan@example.com')
        login = FakeLogin(('jan@example.com', False))
        self.assertIsNone(AlwaysByEmail().authenticate_by_email(login))

    @override_settings(ACCOUNT_USER_MODEL_EMAIL_FIELD=None)
    def test_without_user_email_field_only_verified_rows_match(self):
        user = self.make_user('kim@example.com')
        login = FakeLogin(('kim@example.com', True))
        self.assertIsNone(AlwaysByEmail().authenticate_by_email(login))
        EmailAddress.objects.create(user=user, email='kim@example.com', verified=True)
        self.assertEqual(
            AlwaysByEmail().authenticate_by_email(login), (user, 'kim@example.com')
        )
