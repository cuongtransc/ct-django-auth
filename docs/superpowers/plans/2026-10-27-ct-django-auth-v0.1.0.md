# ct-django-auth v0.1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.1.0 of a public Django package that holds the invite-only, OAuth-only sign-in layer (allauth adapters, policy system checks, admin-login redirect, default dead-end templates, contract-test mixin).

**Architecture:** A reusable Django app `ct_django_auth`. Apps keep their settings explicit; the package's system checks fail on policy drift. The contract-test mixin in `ct_django_auth/testing.py` is both the package's own behavioural suite (run against a minimal project in `tests/`) and what each consuming app inherits.

**Tech Stack:** Python 3.12/3.13, Django 6.0, django-allauth 65.20.x, uv, pytest + pytest-django, ruff, gitleaks, mise, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-27-ct-django-auth-design.md`

## Global Constraints

- Distribution name `ct-django-auth`, import package `ct_django_auth`, version `0.1.0`, license MIT.
- `requires-python = ">=3.12"`. Runtime dependencies exactly: `django>=6.0,<6.1`, `django-allauth[socialaccount]>=65.20.1,<66`. Everything else goes in the `dev` dependency group.
- uv supply-chain policy: `exclude-newer = "14 days"`; `[tool.uv.exclude-newer-package] django-allauth = "2026-10-21"` (65.20.1 accepts oauthlib 4). `uv.lock` is committed.
- Public repository: no consumer app names, domains, IPs, emails, internal paths or real-looking secrets anywhere (code, fixtures, docs, commit messages). Fixtures use `example.com` / `example.test`; the fake GitHub account is login `octo`, id `4242`.
- Commits use the repo-local no-reply identity already configured (`git config user.email` must end in `@users.noreply.github.com`; check before the first commit of each task).
- Style: ruff, `line-length = 88`, `quote-style = "single"`, target `py312`.
- System check IDs and messages are exactly those in Task 4. Template copy is exactly that in Task 5.
- The test project lives in `tests/` (`tests/settings.py`, `tests/urls.py`); pytest-django uses `DJANGO_SETTINGS_MODULE = "tests.settings"`. Its `LOGIN_REDIRECT_URL` is `/home/`.
- Every gate runs through mise: `mise run test`, `mise run lint`, `mise run leaks`, `mise run ci` (= lint + test + leaks). Tools run via `uv run <tool>`, never bare.
- GitHub Actions: every third-party action pinned by a full commit SHA with the version in a trailing comment; the workflow needs no secrets and has `permissions: contents: read`.

## Review Focus

1. A provider email that is not verified must never claim an invite, including when a verified address of another user would match case-insensitively. Owned by Task 2 (`test_unverified_email_does_not_claim_invite`).
2. `/admin/login/?next=https://evil.example.com/` must not send the browser off-site. `admin_login` always redirects to the local `account_login` path; Task 3 pins it (`test_admin_login_never_redirects_off_site`).
3. An app that sets `INVITE_ONLY` to a string such as `'False'` (env read without `bool`) must not silently open sign-up. Task 2 treats only the boolean `False` as open (`test_invite_only_string_false_stays_closed`).
4. A consuming app that overrides only one of the two templates still gets the package's version of the other, never allauth's bare page. Task 5 asserts the package templates win over allauth's by app order (`test_package_templates_shadow_allauth`).
5. A system check must not crash `manage.py check` when a setting points at a dotted path that cannot be imported; it reports E002 instead. Task 4 (`test_e002_unimportable_adapter`).

---

### Task 1: Project scaffold, tooling and leak guard

**Files:**
- Create: `pyproject.toml`, `mise.toml`, `.gitignore`, `LICENSE`, `README.md`, `CHANGELOG.md`, `.githooks/pre-commit`
- Create: `ct_django_auth/__init__.py`, `ct_django_auth/apps.py`
- Create: `tests/__init__.py`, `tests/settings.py`, `tests/urls.py`, `tests/views.py`, `tests/test_package.py`

**Interfaces:**
- Produces: `ct_django_auth.__version__ == '0.1.0'`; `ct_django_auth.apps.CtDjangoAuthConfig` (`name = 'ct_django_auth'`, `ready()` empty for now); test project settings `tests.settings` with `LOGIN_REDIRECT_URL = '/home/'`, URL name `home` at `/home/`.

- [ ] **Step 1: Write the failing test** `tests/test_package.py`

```python
from django.apps import apps

import ct_django_auth


def test_version():
    assert ct_django_auth.__version__ == '0.1.0'


def test_app_is_installed_in_test_project():
    assert apps.get_app_config('ct_django_auth').name == 'ct_django_auth'
```

- [ ] **Step 2: Create `pyproject.toml`** with: build backend hatchling (package `ct_django_auth`, include `ct_django_auth/templates/**`); the Global Constraints' metadata and dependencies; `[dependency-groups] dev = ["pytest>=8", "pytest-django>=4.9", "ruff>=0.15", "requests>=2.32"]`; the uv policy from Global Constraints; `[tool.pytest.ini_options] DJANGO_SETTINGS_MODULE = "tests.settings"`, `pythonpath = ["."]`; `[tool.ruff]` per Global Constraints.

- [ ] **Step 3: Create `mise.toml`**: `[tools] python = "3.13"`, `uv` pinned to the exact version `uv --version` prints, `gitleaks = "8.30.1"`. Tasks:
  - `test`: `uv run pytest -q`
  - `lint`: `uv run ruff check . && uv run ruff format --check .`
  - `leaks`: `gitleaks dir . --redact --no-banner && gitleaks git . --redact --no-banner`
  - `leaks:staged`: `gitleaks git --staged --redact --no-banner .`
  - `hooks`: `git config core.hooksPath .githooks`
  - `ci`: depends on `lint`, `test`, `leaks`; runs `echo 'ci passed'`

- [ ] **Step 4: Create `.githooks/pre-commit`** (executable, `#!/usr/bin/env bash`, `set -euo pipefail`) whose only command is `mise run leaks:staged`. Step 8 activates it with `mise run hooks`.

- [ ] **Step 5: Create the test project.** `tests/settings.py`:

```python
SECRET_KEY = 'test-only-not-a-secret'
DEBUG = False
ALLOWED_HOSTS = ['testserver']
USE_TZ = True
ROOT_URLCONF = 'tests.urls'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'ct_django_auth',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
]
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ]
        },
    }
]
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
LOGIN_REDIRECT_URL = '/home/'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'APP': {'client_id': 'test-id', 'secret': 'test-secret', 'key': ''},
        'SCOPE': ['user:email'],
    }
}
```

`ct_django_auth` is listed **before** `allauth` so its templates shadow allauth's (Task 5 relies on this; README states it). `tests/urls.py`: `path('', include('ct_django_auth.urls'))` is added in Task 3; for now `path('admin/', admin.site.urls)`, `path('accounts/', include('allauth.urls'))`, `path('home/', views.home, name='home')`. `tests/views.py`: `home(request)` returns `HttpResponse('home')`.

- [ ] **Step 6: Create `ct_django_auth/__init__.py`** (`__version__ = '0.1.0'`) and `apps.py` (`CtDjangoAuthConfig`, `default_auto_field = 'django.db.models.BigAutoField'`).

- [ ] **Step 7: Create `LICENSE`** (MIT, `Copyright (c) 2026 Cuong Tran`), `.gitignore` (`.venv/`, `__pycache__/`, `*.egg-info/`, `dist/`, `.pytest_cache/`, `.ruff_cache/`), `CHANGELOG.md` (`## 0.1.0 — unreleased`), and a one-paragraph `README.md` placeholder (Task 7 fills it).

- [ ] **Step 8: Lock and run** `uv lock && mise run hooks && mise run test`
  Expected: `2 passed`.

- [ ] **Step 9: Run** `mise run lint && mise run leaks`
  Expected: ruff clean; gitleaks `no leaks found` twice.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "build: scaffold package, test project and leak guard"
```

---

### Task 2: Adapters and the contract-test mixin

**Files:**
- Create: `ct_django_auth/adapters.py`, `ct_django_auth/testing.py`
- Create: `tests/test_contract.py`, `tests/test_adapters.py`
- Modify: `tests/settings.py` (adapter and email-authentication settings)

**Interfaces:**
- Consumes: test project from Task 1.
- Produces:
  - `ct_django_auth.adapters.InviteOnlyAccountAdapter(DefaultAccountAdapter)`; `InviteOnlySocialAccountAdapter(DefaultSocialAccountAdapter)`.
  - `ct_django_auth.adapters.invite_only_enabled() -> bool`: `getattr(settings, 'INVITE_ONLY', True) is not False`.
  - `ct_django_auth.testing.GITHUB_TEST_APP: dict` (the `SOCIALACCOUNT_PROVIDERS` value from Task 1 Step 5).
  - `ct_django_auth.testing.fake_github_api(email: str, verified: bool = True)` → context manager patching `requests.Session.request`.
  - `ct_django_auth.testing.GitHubLoginMixin`: `setUp` overrides `SOCIALACCOUNT_PROVIDERS` with `GITHUB_TEST_APP`; helpers `github_login(self, email: str, verified: bool = True) -> HttpResponse` and `signed_in_pk(self) -> str | None`. No test methods.
  - `ct_django_auth.testing.OAuthContractTests(GitHubLoginMixin)`: class attribute `login_redirect_url: str`, abstract `make_invitee(self, email: str) -> User` (raises `NotImplementedError`). Holds the contract test methods; later tasks add more.

- [ ] **Step 1: Add to `tests/settings.py`**

```python
ACCOUNT_ADAPTER = 'ct_django_auth.adapters.InviteOnlyAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'ct_django_auth.adapters.InviteOnlySocialAccountAdapter'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
INVITE_ONLY = True
```

- [ ] **Step 2: Write `ct_django_auth/testing.py` test helpers and the first contract tests.** `fake_github_api` answers, matched on the URL without query string:
  - `https://github.com/login/oauth/access_token` → `{'access_token': 'tok', 'token_type': 'bearer', 'scope': 'user:email'}`
  - `https://api.github.com/user` → `{'id': 4242, 'login': 'octo', 'name': 'Octo', 'email': email}`
  - `https://api.github.com/user/emails` → `[{'email': email, 'primary': True, 'verified': verified}]`

  each as a `requests.Response` with status 200 and `Content-Type: application/json`. `github_login` POSTs `/accounts/github/login/`, asserts a 302, reads `state` from the `Location` query, then GETs `/accounts/github/login/callback/` with `code='c'` and that state inside `fake_github_api(email, verified)`. `GitHubLoginMixin.setUp` calls `super().setUp()`, enables `override_settings(SOCIALACCOUNT_PROVIDERS=GITHUB_TEST_APP)` and registers its disable with `addCleanup`, so an app's own provider settings never matter.

  `testing.py` imports: `json`, `contextlib.contextmanager`, `unittest.mock`, `urllib.parse.parse_qs, urlparse`, `requests`, `allauth.socialaccount.models.SocialAccount`, `django.contrib.auth.get_user_model`, `django.test.override_settings`, `django.urls.reverse`. It must not import `pytest`: apps run it under Django's test runner.

  Contract tests in `OAuthContractTests` (complete code):

```python
    def test_get_does_not_start_oauth(self):
        resp = self.client.get('/accounts/github/login/')
        self.assertNotIn('github.com', resp.get('Location', ''))

    def test_password_signup_is_closed(self):
        self.client.post(
            '/accounts/signup/',
            {'email': 'mallory@example.com', 'password1': 'x9!Kq2#vL', 'password2': 'x9!Kq2#vL'},
        )
        self.assertFalse(get_user_model().objects.filter(email='mallory@example.com').exists())

    def test_invitee_signs_in_and_is_linked(self):
        invitee = self.make_invitee('alice@example.com')
        resp = self.github_login('alice@example.com')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], self.login_redirect_url)
        self.assertEqual(self.signed_in_pk(), str(invitee.pk))
        self.assertTrue(SocialAccount.objects.filter(user=invitee, provider='github').exists())

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
        self.assertFalse(get_user_model().objects.filter(email='stranger@example.com').exists())
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
```

- [ ] **Step 3: Create `tests/test_contract.py`**

```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from ct_django_auth.testing import OAuthContractTests


class TestProjectContract(OAuthContractTests, TestCase):
    login_redirect_url = '/home/'

    def make_invitee(self, email):
        return get_user_model().objects.create_user(username=email, email=email)
```

- [ ] **Step 4: Create `tests/test_adapters.py`** (package-only behaviour, not part of the app contract)

```python
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
```

- [ ] **Step 5: Run** `mise run test`
  Expected: FAIL; adapter imports error (`ct_django_auth.adapters` missing).

- [ ] **Step 6: Implement `ct_django_auth/adapters.py`** per the spec's Adapters section:
  - `invite_only_enabled() -> bool` as in Interfaces.
  - `InviteOnlyAccountAdapter.is_open_for_signup(self, request) -> bool`: `False`.
  - `InviteOnlySocialAccountAdapter.is_open_for_signup(self, request, sociallogin) -> bool`: `not invite_only_enabled()`.
  - `is_auto_signup_allowed(self, request, sociallogin) -> bool`: `True`.
  - `on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None) -> None`: when `request.user.is_authenticated`, raise `allauth.core.exceptions.ImmediateHttpResponse(redirect(settings.LOGIN_REDIRECT_URL))`.
  - `authenticate_by_email(self, sociallogin)`: return `super().authenticate_by_email(sociallogin)` when truthy. Otherwise, for each address in `sociallogin.email_addresses` that is `verified` and passes `self.can_authenticate_by_email(sociallogin, address.email)`, take `get_user_model().objects.filter(email__iexact=address.email)[:2]` and return `(user, address.email)` when exactly one user matches. Return `None` otherwise.

- [ ] **Step 7: Run** `mise run test`
  Expected: all pass.

- [ ] **Step 8: Run** `mise run lint`, fix, then commit

```bash
git add -A
git commit -m "feat: invite-only adapters and OAuth contract tests"
```

---

### Task 3: `admin_login` view and URLconf

**Files:**
- Create: `ct_django_auth/views.py`, `ct_django_auth/urls.py`
- Modify: `tests/urls.py` (include `ct_django_auth.urls` first)
- Modify: `ct_django_auth/testing.py` (two contract tests)
- Create: `tests/test_views.py`

**Interfaces:**
- Consumes: `OAuthContractTests` from Task 2.
- Produces: `ct_django_auth.views.admin_login(request, extra_context=None) -> HttpResponse`; `ct_django_auth.urls.urlpatterns = [path('admin/login/', admin_login, name='ct_auth_admin_login')]`.

- [ ] **Step 1: Add to `OAuthContractTests`**

```python
    def test_admin_login_sends_staff_to_oauth_keeping_next(self):
        with self.settings(DEBUG=False):
            resp = self.client.get('/admin/login/?next=/admin/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('account_login') + '?next=/admin/')

    def test_admin_password_post_does_not_sign_in(self):
        user = self.make_invitee('root@example.com')
        user.is_staff = True
        user.set_password('x9!Kq2#vL')
        user.save()
        with self.settings(DEBUG=False):
            self.client.post('/admin/login/', {'username': user.get_username(), 'password': 'x9!Kq2#vL'})
        self.assertIsNone(self.signed_in_pk())
```

- [ ] **Step 2: Create `tests/test_views.py`**

```python
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
```

- [ ] **Step 3: Run** `mise run test`
  Expected: the new tests FAIL (`/admin/login/` serves Django's form).

- [ ] **Step 4: Implement** `admin_login`: `settings.DEBUG` → `admin.site.login(request, extra_context)`; otherwise `HttpResponseRedirect(reverse('account_login') + ('?' + request.META['QUERY_STRING'] if request.META.get('QUERY_STRING') else ''))`. Create `urls.py` per Interfaces; put `path('', include('ct_django_auth.urls'))` first in `tests/urls.py`.

- [ ] **Step 5: Run** `mise run test`
  Expected: all pass.

- [ ] **Step 6: Lint and commit**

```bash
git add -A
git commit -m "feat: admin_login sends staff to OAuth outside DEBUG"
```

---

### Task 4: System checks

**Files:**
- Create: `ct_django_auth/checks.py`, `tests/test_checks.py`, `tests/adapters.py`, `tests/urls_without_package.py`
- Modify: `ct_django_auth/apps.py` (`ready()` imports `checks` so they register)

**Interfaces:**
- Consumes: adapters (Task 2), `admin_login` (Task 3).
- Produces: check functions registered with `django.core.checks.register()` (default tags). Each returns `list[CheckMessage]`. Exact IDs and messages:

| ID | Level | `msg` | `hint` |
|---|---|---|---|
| `ct_auth.E001` | Error | `SOCIALACCOUNT_LOGIN_ON_GET must be False: a plain link would start an OAuth sign-in (login CSRF).` | `Remove the setting; sign-in buttons POST with {% csrf_token %}.` |
| `ct_auth.E002` | Error | `{name} must be ct_django_auth.adapters.{expected} or a subclass of it.` | `Set {name} = 'ct_django_auth.adapters.{expected}'.` |
| `ct_auth.E003` | Error | `{name} must be True for invites to match the provider's verified email.` | `Set {name} = True.` |
| `ct_auth.E004` | Error | `/admin/login/ must resolve to ct_django_auth.views.admin_login.` | `Include ct_django_auth.urls before admin.site.urls in the root URLconf.` |
| `ct_auth.W001` | Warning | `Provider '{provider}' returns no email: a new user signing in through it can never match an invite.` | `Invite such users by linking their account in the admin, or remove the provider.` |

E002 runs once per setting: `name='ACCOUNT_ADAPTER', expected='InviteOnlyAccountAdapter'` and `name='SOCIALACCOUNT_ADAPTER', expected='InviteOnlySocialAccountAdapter'`; an unset setting, an unimportable path, or a non-subclass all yield E002. E003 runs once for each of `SOCIALACCOUNT_QUERY_EMAIL`, `SOCIALACCOUNT_EMAIL_AUTHENTICATION`, `SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT`. W001 fires for each entry of `settings.INSTALLED_APPS` equal to `allauth.socialaccount.providers.<id>` with `<id>` in `{'twitter', 'twitter_oauth2'}` (read the setting, not the app registry).

- [ ] **Step 1: Write `tests/test_checks.py`**

```python
from django.core.checks import run_checks
from django.test import SimpleTestCase, override_settings


def ids():
    return sorted(m.id for m in run_checks() if m.id and m.id.startswith('ct_auth.'))


class CheckTests(SimpleTestCase):
    def test_test_project_is_clean(self):
        self.assertEqual(ids(), [])

    @override_settings(SOCIALACCOUNT_LOGIN_ON_GET=True)
    def test_e001_login_on_get(self):
        self.assertEqual(ids(), ['ct_auth.E001'])

    @override_settings(SOCIALACCOUNT_ADAPTER='allauth.socialaccount.adapter.DefaultSocialAccountAdapter')
    def test_e002_wrong_adapter(self):
        self.assertEqual(ids(), ['ct_auth.E002'])

    @override_settings(ACCOUNT_ADAPTER='no.such.Adapter')
    def test_e002_unimportable_adapter(self):
        self.assertEqual(ids(), ['ct_auth.E002'])

    @override_settings(SOCIALACCOUNT_ADAPTER='tests.adapters.AppSocialAdapter')
    def test_subclass_adapter_is_accepted(self):
        self.assertEqual(ids(), [])

    @override_settings(SOCIALACCOUNT_EMAIL_AUTHENTICATION=False)
    def test_e003_email_authentication_off(self):
        self.assertEqual(ids(), ['ct_auth.E003'])

    @override_settings(ROOT_URLCONF='tests.urls_without_package')
    def test_e004_admin_login_not_routed(self):
        self.assertEqual(ids(), ['ct_auth.E004'])

    @override_settings()
    def test_w001_provider_without_email(self):
        # The check reads INSTALLED_APPS names; it does not need the app loaded.
        from django.conf import settings

        settings.INSTALLED_APPS = [
            *settings.INSTALLED_APPS,
            'allauth.socialaccount.providers.twitter_oauth2',
        ]
        self.assertEqual(ids(), ['ct_auth.W001'])
```

Create the fixtures it needs: `tests/adapters.py` (`class AppSocialAdapter(InviteOnlySocialAccountAdapter): pass`) and `tests/urls_without_package.py` (Task 3's `tests/urls.py` minus the `ct_django_auth.urls` include).

- [ ] **Step 2: Run** `mise run test`
  Expected: FAIL; every check test except `test_test_project_is_clean` and `test_subclass_adapter_is_accepted`.

- [ ] **Step 3: Implement `ct_django_auth/checks.py`** with the table above. Use `django.utils.module_loading.import_string` inside `try/except ImportError` for E002, and `django.urls.resolve('/admin/login/')` inside `try/except Resolver404` for E004, comparing `match.func is admin_login`. Import `checks` in `CtDjangoAuthConfig.ready()`.

- [ ] **Step 4: Run** `mise run test`
  Expected: all pass. Then `uv run django-admin check --settings=tests.settings --pythonpath=.`
  Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Lint and commit**

```bash
git add -A
git commit -m "feat: system checks fail on sign-in policy drift"
```

---

### Task 5: Default dead-end templates

**Files:**
- Create: `ct_django_auth/templates/account/signup_closed.html`, `ct_django_auth/templates/socialaccount/authentication_error.html`
- Modify: `ct_django_auth/testing.py` (one contract test)
- Create: `tests/test_templates.py`

**Interfaces:**
- Consumes: contract mixin (Task 2).
- Produces: the two templates; the context they use is only `{% url 'account_login' %}`.

Exact copy (spec, "Default templates"). Each file is a full `<!doctype html>` document, `lang="en"`, with a `<meta name="viewport" content="width=device-width, initial-scale=1">` and no external assets, no `{% extends %}`:

| Template | `<title>` | `<h1>` | `<p>` | link text |
|---|---|---|---|---|
| `account/signup_closed.html` | `Sign-up closed` | `Sign-up is invite-only` | `This account does not have access. Ask an administrator for an invite to the email you signed in with.` | `Back to sign in` |
| `socialaccount/authentication_error.html` | `Sign-in failed` | `Sign-in did not complete` | `The sign-in link expired or was already used. Please sign in again.` | `Back to sign in` |

- [ ] **Step 1: Add to `OAuthContractTests`**

```python
    def test_failed_callback_page_offers_sign_in_only(self):
        resp = self.client.get('/accounts/github/login/callback/', {'code': 'c', 'state': 'stale'})
        self.assertEqual(resp.status_code, 401)
        self.assertContains(resp, f'href="{reverse("account_login")}"', status_code=401)
        self.assertNotContains(resp, reverse('account_signup'), status_code=401)
```

- [ ] **Step 2: Write `tests/test_templates.py`**

```python
from django.template.loader import get_template
from django.test import SimpleTestCase


class TemplateTests(SimpleTestCase):
    def test_package_templates_shadow_allauth(self):
        for name in ('account/signup_closed.html', 'socialaccount/authentication_error.html'):
            origin = get_template(name).origin.name
            self.assertIn('ct_django_auth', origin, name)

    def test_signup_closed_copy(self):
        html = get_template('account/signup_closed.html').render({})
        self.assertIn('Sign-up is invite-only', html)
        self.assertIn('Back to sign in', html)
```

- [ ] **Step 3: Run** `mise run test`; expected FAIL (allauth's templates are served).
- [ ] **Step 4: Write the two templates** per the table.
- [ ] **Step 5: Run** `mise run test`; expected all pass.
- [ ] **Step 6: Lint and commit**

```bash
git add -A
git commit -m "feat: default dead-end templates"
```

---

### Task 6: README, changelog and CI workflow

**Files:**
- Modify: `README.md`, `CHANGELOG.md`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: everything above. Produces documentation and CI only.

- [ ] **Step 1: Write `README.md`**, generic, no consumer names. Sections: what it does (one paragraph, the spec's Purpose without the incident list); Install (the `[tool.uv.sources]` block with `rev = "<commit sha>"` and why a SHA, linking ADR 0003); Configure (the spec's "Settings the app writes" block, the URLconf block, and the rule that `ct_django_auth` is listed before `allauth` in `INSTALLED_APPS`); System checks (the Task 4 table, ID + when); Templates (paths and how to override); Contract tests (the `tests/test_contract.py` example from Task 2 Step 3); Security (link to ADR 0002; report issues through GitHub private vulnerability reporting).

- [ ] **Step 2: Fill `CHANGELOG.md`** `## 0.1.0` with one line per feature (adapters, checks E001–E004/W001, admin_login, templates, contract tests).

- [ ] **Step 3: Write `.github/workflows/ci.yml`**: on `push` to `main` and `pull_request`; `permissions: contents: read`; job `test` with matrix `python: ['3.12', '3.13']` running checkout (with `fetch-depth: 0` so gitleaks sees history), `astral-sh/setup-uv` with that Python, `uv sync --all-groups --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`; job `leaks` installing gitleaks 8.30.1 from its GitHub release tarball with the release's published SHA-256 verified, then `gitleaks git . --redact --no-banner`. Resolve each action's SHA with `git ls-remote https://github.com/<owner>/<repo> refs/tags/<tag>` and pin `uses: <owner>/<repo>@<sha> # <tag>`.

- [ ] **Step 4: Run** `mise run ci`
  Expected: `ci passed`.

- [ ] **Step 5: Leak review before commit**: `rg -n -i -f .git/info/leak-denylist .` → no matches (exit 1); `git log --format='%ae' | sort -u` → only the no-reply address. The denylist (consumer names, domains, personal email, local paths) lives only in `.git/info/`, never in a tracked file: writing those terms into the repo would leak them.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: README, changelog and CI workflow"
```

---

### Task 7: Publish v0.1.0 (human-gated)

Every step here is outward-facing. Each needs the owner's explicit go-ahead in chat; the executor stops before Step 2 and asks.

- [ ] **Step 1: Final local gate**: `mise run ci` green; `gitleaks git . --redact --no-banner` → `no leaks found`; `git log --format='%an <%ae>' | sort -u` → only `Cuong Tran <…@users.noreply.github.com>`.
- [ ] **Step 2 (owner):** create the public repository `cuongtransc/ct-django-auth` on GitHub, empty (no README, no license).
- [ ] **Step 3 (owner):** on GitHub enable secret scanning + push protection, private vulnerability reporting, Dependabot alerts; protect `main` (pull request required, status checks `test` and `leaks` required, no force-push); and in personal settings, "Block command line pushes that expose my email".
- [ ] **Step 4:** push `feat/v0.1.0`, open a PR to `main` with the `git-mr` skill; wait for CI green; the owner merges.
- [ ] **Step 5:** on the merged `main` commit, `git tag -s v0.1.0 -m "v0.1.0"` and `git push origin v0.1.0`. Record the commit SHA: it is what consuming apps pin.
