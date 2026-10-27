from django.core.checks import run_checks
from django.test import SimpleTestCase, override_settings

from ct_django_auth.checks import check_sign_in_policy


def ids():
    return sorted(m.id for m in run_checks() if m.id and m.id.startswith('ct_auth.'))


class CheckTests(SimpleTestCase):
    def test_test_project_is_clean(self):
        self.assertEqual(ids(), [])

    @override_settings(SOCIALACCOUNT_LOGIN_ON_GET=True)
    def test_e001_login_on_get(self):
        self.assertEqual(ids(), ['ct_auth.E001'])

    @override_settings(
        SOCIALACCOUNT_ADAPTER='allauth.socialaccount.adapter.DefaultSocialAccountAdapter'
    )
    def test_e002_wrong_adapter(self):
        self.assertEqual(ids(), ['ct_auth.E002'])

    @override_settings(ACCOUNT_ADAPTER='no.such.Adapter')
    def test_e002_unimportable_adapter(self):
        # allauth's own adapter_check raises on an unimportable adapter, so
        # run_checks() cannot reach ours; call the check directly.
        found = [m.id for m in check_sign_in_policy(None)]
        self.assertEqual(found, ['ct_auth.E002'])

    def test_e002_non_string_adapter(self):
        for value in (42, None, ['x']):
            with self.subTest(value=value), self.settings(ACCOUNT_ADAPTER=value):
                found = [m.id for m in check_sign_in_policy(None)]
                self.assertEqual(found, ['ct_auth.E002'])

    @override_settings(SOCIALACCOUNT_ADAPTER='tests.adapters.AppSocialAdapter')
    def test_subclass_adapter_is_accepted(self):
        self.assertEqual(ids(), [])

    @override_settings(SOCIALACCOUNT_EMAIL_AUTHENTICATION=False)
    def test_e003_email_authentication_off(self):
        self.assertEqual(ids(), ['ct_auth.E003'])

    @override_settings(ROOT_URLCONF='tests.urls_without_package')
    def test_e004_admin_login_not_routed(self):
        self.assertEqual(ids(), ['ct_auth.E004'])

    @override_settings(SOCIALACCOUNT_ONLY=False)
    def test_e005_socialaccount_only_off(self):
        self.assertEqual(ids(), ['ct_auth.E005'])

    @override_settings()
    def test_e005_socialaccount_only_absent(self):
        from django.conf import settings

        del settings.SOCIALACCOUNT_ONLY
        self.assertEqual(ids(), ['ct_auth.E005'])

    def test_e006_provider_verified_email(self):
        providers = {
            'github': {'APP': {'client_id': 'x', 'secret': 'y'}},
            'google': {'VERIFIED_EMAIL': True},
        }
        with self.settings(SOCIALACCOUNT_PROVIDERS=providers):
            found = [m for m in check_sign_in_policy(None) if m.id == 'ct_auth.E006']
        self.assertEqual(len(found), 1)
        self.assertIn("SOCIALACCOUNT_PROVIDERS['google']", found[0].msg)

    def test_e006_any_value_but_false(self):
        for value in (True, 'yes', None, 1):
            providers = {'github': {'VERIFIED_EMAIL': value}}
            with (
                self.subTest(value=value),
                self.settings(SOCIALACCOUNT_PROVIDERS=providers),
            ):
                self.assertEqual(ids(), ['ct_auth.E006'])

    @override_settings(SOCIALACCOUNT_PROVIDERS={'github': {'VERIFIED_EMAIL': False}})
    def test_e006_explicit_false_is_accepted(self):
        self.assertEqual(ids(), [])

    @override_settings()
    def test_w001_provider_without_email(self):
        # The check reads INSTALLED_APPS names; it does not need the app loaded.
        from django.conf import settings

        settings.INSTALLED_APPS = [
            *settings.INSTALLED_APPS,
            'allauth.socialaccount.providers.twitter_oauth2',
        ]
        self.assertEqual(ids(), ['ct_auth.W001'])
