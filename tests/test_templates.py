from django.template.loader import get_template
from django.test import SimpleTestCase


class TemplateTests(SimpleTestCase):
    def test_package_templates_shadow_allauth(self):
        for name in (
            'account/signup_closed.html',
            'socialaccount/authentication_error.html',
        ):
            origin = get_template(name).origin.name
            self.assertIn('ct_django_auth', origin, name)

    def test_signup_closed_copy(self):
        html = get_template('account/signup_closed.html').render({})
        self.assertIn('Sign-up is invite-only', html)
        self.assertIn('Back to sign in', html)
