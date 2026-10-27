# ct-django-auth

Invite-only, OAuth-only sign-in layer on [django-allauth](https://allauth.org).
Several Django apps sign users in the same way: OAuth only, and only people an
admin has invited. This package holds that layer once: allauth adapters, system
checks that fail when an app's settings drift from the policy, an
`/admin/login/` view that sends staff to OAuth outside `DEBUG`, two default
templates, and a contract-test mixin each app runs against its own settings.

Supported: Python 3.12 and 3.13, Django `>=6.0,<6.1`, django-allauth
`>=65.20.1,<66`.

## Install

Pin a commit, not a tag. A tag can be moved; a SHA cannot, so an upgrade is a
reviewable diff ([ADR 0003](docs/adr/0003-pin-by-commit-sha.md)).

```toml
[tool.uv.sources]
ct-django-auth = { git = "https://github.com/cuongtransc/ct-django-auth", rev = "<40-char commit sha>" }  # v0.1.0
```

## Configure

The package never writes your settings. Keep these explicit
([ADR 0001](docs/adr/0001-explicit-settings-enforced-by-checks.md)):

```python
INSTALLED_APPS += [
    'ct_django_auth',  # must come BEFORE 'allauth', or allauth's bare templates win
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
]
ACCOUNT_ADAPTER = 'ct_django_auth.adapters.InviteOnlyAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'ct_django_auth.adapters.InviteOnlySocialAccountAdapter'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
INVITE_ONLY = True  # default when absent; False lets unknown emails sign up
# SOCIALACCOUNT_LOGIN_ON_GET stays unset (False).
```

Root URLconf, before `admin.site.urls`:

```python
urlpatterns = [
    path('', include('ct_django_auth.urls')),
    path('admin/', admin.site.urls),
]
```

Behaviour:

- An invite is an existing user whose `email` field matches the provider's
  verified address, in any case. The match uses the `email` field of the user
  model. Two users differing only by case are treated as no invite.
- `admin_login` shows Django admin's password form when `DEBUG` is true;
  otherwise it redirects (302) to `account_login`, keeping the query string.
  It uses `django.contrib.admin.site`; a custom `AdminSite` is not supported in
  0.1.0.

## System checks

| ID | Fails when |
|---|---|
| `ct_auth.E001` | `SOCIALACCOUNT_LOGIN_ON_GET` is true |
| `ct_auth.E002` | `ACCOUNT_ADAPTER` or `SOCIALACCOUNT_ADAPTER` is not the package's adapter or a subclass |
| `ct_auth.E003` | `SOCIALACCOUNT_QUERY_EMAIL`, `SOCIALACCOUNT_EMAIL_AUTHENTICATION` or `SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT` is not true |
| `ct_auth.E004` | `/admin/login/` does not resolve to `ct_django_auth.views.admin_login` |
| `ct_auth.W001` | a configured provider returns no email (`twitter`, `twitter_oauth2`): a new user signing in through it can never match an invite |

Notes:

- Errors stop `runserver`, `migrate` and Django's test runner. pytest-django
  does not run system checks: run `python manage.py check` in your CI so
  E001-E004 fail the build.
- E004 looks for the literal path `/admin/login/`. An app that mounts the admin
  elsewhere, or under `i18n_patterns`, will see E004.
- An `ACCOUNT_ADAPTER` or `SOCIALACCOUNT_ADAPTER` path that cannot be imported
  makes allauth's own check fail with an `ImportError` before E002 is reported.

## Templates

Plain, self-contained HTML (no `{% extends %}`), with one action, "Back to
sign in":

- `account/signup_closed.html`
- `socialaccount/authentication_error.html` (served with status 401)

Override either by placing a template at the same path in your own `templates/`
directory, ahead of this app's.

## Contract tests

`OAuthContractTests` runs the whole sign-in contract against your settings and
URLconf, with a fake GitHub API (no network). Set `login_redirect_url` and
implement `make_invitee`:

```python
# tests/test_contract.py
from django.contrib.auth import get_user_model
from django.test import TestCase

from ct_django_auth.testing import OAuthContractTests


class TestProjectContract(OAuthContractTests, TestCase):
    login_redirect_url = '/home/'

    def make_invitee(self, email):
        return get_user_model().objects.create_user(username=email, email=email)
```

## Security

The repository is public and holds no secrets
([ADR 0002](docs/adr/0002-public-repository.md)). Report vulnerabilities
through GitHub private vulnerability reporting on this repository, not in a
public issue.

## License

MIT
