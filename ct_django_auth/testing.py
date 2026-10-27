"""Test support: a fake GitHub OAuth server and the app contract tests.

Apps subclass ``OAuthContractTests`` next to a Django ``TestCase``. Nothing
here imports pytest, so it runs under Django's own test runner.
"""

import json
from contextlib import contextmanager
from unittest import mock
from urllib.parse import parse_qs, urlparse

import requests
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

GITHUB_TEST_APP = {
    'github': {
        'APP': {'client_id': 'test-id', 'secret': 'test-secret', 'key': ''},
        'SCOPE': ['user:email'],
    }
}


def _json_response(payload):
    resp = requests.Response()
    resp.status_code = 200
    resp.headers['Content-Type'] = 'application/json'
    resp._content = json.dumps(payload).encode()
    return resp


@contextmanager
def fake_github_api(email, verified=True):
    """Answer GitHub's token, user and emails endpoints without network."""
    answers = {
        'https://github.com/login/oauth/access_token': {
            'access_token': 'tok',
            'token_type': 'bearer',
            'scope': 'user:email',
        },
        'https://api.github.com/user': {
            'id': 4242,
            'login': 'octo',
            'name': 'Octo',
            'email': email,
        },
        'https://api.github.com/user/emails': [
            {'email': email, 'primary': True, 'verified': verified}
        ],
    }

    def fake_request(self, method, url, *args, **kwargs):
        return _json_response(answers[url.split('?')[0]])

    with mock.patch.object(requests.Session, 'request', fake_request):
        yield


class GitHubLoginMixin:
    def setUp(self):
        super().setUp()
        override = override_settings(SOCIALACCOUNT_PROVIDERS=GITHUB_TEST_APP)
        override.enable()
        self.addCleanup(override.disable)

    def github_login(self, email, verified=True):
        resp = self.client.post(reverse('github_login'))
        assert resp.status_code == 302, resp.status_code
        state = parse_qs(urlparse(resp['Location']).query)['state'][0]
        with fake_github_api(email, verified):
            return self.client.get(
                reverse('github_callback'), {'code': 'c', 'state': state}
            )

    def signed_in_pk(self):
        return self.client.session.get('_auth_user_id')


class OAuthContractTests(GitHubLoginMixin):
    login_redirect_url: str

    def make_invitee(self, email):
        raise NotImplementedError

    def test_get_does_not_start_oauth(self):
        resp = self.client.get('/accounts/github/login/')
        self.assertNotIn('github.com', resp.get('Location', ''))

    def test_password_signup_is_closed(self):
        self.client.post(
            '/accounts/signup/',
            {
                'email': 'mallory@example.com',
                'password1': 'x9!Kq2#vL',
                'password2': 'x9!Kq2#vL',
            },
        )
        self.assertFalse(
            get_user_model().objects.filter(email='mallory@example.com').exists()
        )

    def test_invitee_signs_in_and_is_linked(self):
        invitee = self.make_invitee('alice@example.com')
        resp = self.github_login('alice@example.com')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], self.login_redirect_url)
        self.assertEqual(self.signed_in_pk(), str(invitee.pk))
        self.assertTrue(
            SocialAccount.objects.filter(user=invitee, provider='github').exists()
        )

    def test_invite_matches_regardless_of_case(self):
        invitee = self.make_invitee('bob@example.com')
        get_user_model().objects.filter(pk=invitee.pk).update(email='Bob@Example.COM')
        self.github_login('bob@example.com')
        self.assertEqual(self.signed_in_pk(), str(invitee.pk))

    def test_ambiguous_case_match_is_refused(self):
        a = self.make_invitee('eve1@example.com')
        b = self.make_invitee('eve2@example.com')
        get_user_model().objects.filter(pk=a.pk).update(email='Eve@Example.com')
        get_user_model().objects.filter(pk=b.pk).update(email='EVE@example.com')
        self.github_login('eve@example.com')
        self.assertIsNone(self.signed_in_pk())

    def test_unverified_email_does_not_claim_invite(self):
        invitee = self.make_invitee('carol@example.com')
        get_user_model().objects.filter(pk=invitee.pk).update(email='Carol@Example.com')
        self.github_login('carol@example.com', verified=False)
        self.assertIsNone(self.signed_in_pk())
        self.assertFalse(SocialAccount.objects.filter(user=invitee).exists())

    def test_unknown_email_is_refused_without_account(self):
        with self.settings(INVITE_ONLY=True):
            resp = self.github_login('stranger@example.com')
        self.assertFalse(
            get_user_model().objects.filter(email='stranger@example.com').exists()
        )
        self.assertIsNone(self.signed_in_pk())
        if resp.status_code == 302:
            self.assertIn('signup/closed', resp['Location'])
        else:
            self.assertEqual(resp.status_code, 200)

    def test_refreshed_callback_sends_signed_in_user_on(self):
        self.make_invitee('erin@example.com')
        resp = self.client.post('/accounts/github/login/')
        state = parse_qs(urlparse(resp['Location']).query)['state'][0]
        query = {'code': 'c', 'state': state}
        with fake_github_api('erin@example.com'):
            self.client.get('/accounts/github/login/callback/', query)
            resp = self.client.get('/accounts/github/login/callback/', query)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], self.login_redirect_url)
