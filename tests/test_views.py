from django.test import TestCase, override_settings
from django.urls import reverse


class AdminLoginViewTests(TestCase):
    @override_settings(DEBUG=False)
    def test_admin_login_never_redirects_off_site(self):
        resp = self.client.get('/admin/login/?next=https://evil.example.com/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['Location'].startswith(reverse('account_login')))

    @override_settings(DEBUG=True)
    def test_debug_keeps_admin_password_form(self):
        resp = self.client.get('/admin/login/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="password"')

    @override_settings(DEBUG=False, LOGIN_URL='/login/')
    def test_admin_login_goes_to_the_apps_login_url(self):
        resp = self.client.get('/admin/login/?next=/admin/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/login/?next=/admin/')
