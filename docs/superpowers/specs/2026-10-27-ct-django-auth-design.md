# ct-django-auth: design

Date: 2026-10-27
Status: draft, awaiting review

## Purpose

Several Django apps sign users in the same way: OAuth only, through
django-allauth, and only people an admin has invited. Each app carried its own
copy of that layer, and the copies drifted:

- one bug (a refreshed OAuth callback showing allauth's bare error page) had to
  be fixed once per app;
- one rule (matching an invite's email regardless of case) was written two
  different ways;
- one app enabled GET-initiated OAuth (login CSRF) while the others refused it.

`ct-django-auth` holds that layer once. A fix lands in one place; each app bumps
one pinned commit; a shared contract test proves the behaviour on every app's
own settings.

Success: the next auth fix is one change here plus a version bump per app, and
an app whose settings drift from the policy fails `manage.py check` in its CI.

## Scope

In:

- allauth adapters: invite-only sign-in, password sign-up closed, auto sign-up,
  callback errors, case-insensitive invite matching;
- Django system checks that fail when an app's settings break the policy;
- an `/admin/login/` view that sends staff to OAuth outside `DEBUG`;
- default templates for the two allauth dead-end pages;
- a contract-test mixin each app runs against its own settings.

Out (each app keeps these):

- what a newly signed-up user may see (an approval step, per-project roles);
- notifications on sign-up;
- the look of the sign-in page and of the dead-end pages (apps override the
  default templates);
- the user model.

Policy: **OAuth only.** No password form outside `DEBUG`, neither allauth's nor
Django admin's. `DEBUG` keeps the admin password form for local seed data.

## Supported versions

- Python 3.12 and 3.13
- Django `>=6.0,<6.1`
- django-allauth `>=65.20.1,<66` (65.20.1 is the first to accept oauthlib 4)

These are the package's only runtime dependencies.

## Package layout and public API

```
ct_django_auth/
  apps.py       CtDjangoAuthConfig: registers the system checks
  adapters.py   InviteOnlyAccountAdapter, InviteOnlySocialAccountAdapter
  checks.py     ct_auth.E001..E004, ct_auth.W001
  views.py      admin_login
  urls.py       urlpatterns = [path('admin/login/', admin_login)]
  templates/
    account/signup_closed.html
    socialaccount/authentication_error.html
  testing.py    OAuthContractTests, fake_github_api()
```

### Adapters

`InviteOnlyAccountAdapter(DefaultAccountAdapter)`

- `is_open_for_signup()` → `False`. No email/password accounts, ever.

`InviteOnlySocialAccountAdapter(DefaultSocialAccountAdapter)`

- `is_open_for_signup()` → `not settings.INVITE_ONLY`. `INVITE_ONLY` defaults to
  `True` when the setting is absent.
- `is_auto_signup_allowed()` → `True`. No social sign-up confirmation form.
- `on_authentication_error()`: when the request's user is already signed in,
  raise `ImmediateHttpResponse(redirect(settings.LOGIN_REDIRECT_URL))`;
  otherwise fall through to the error page.
- `authenticate_by_email()`: allauth's exact match first; if none, a
  case-insensitive match on each **verified** provider address, accepted only
  when exactly one user matches.

Apps that need more subclass these (for example, to record a pending sign-up).

### Settings the app writes

The package never writes an app's settings. The app keeps these explicit:

```python
INSTALLED_APPS += ['allauth', 'allauth.account', 'allauth.socialaccount',
                   'ct_django_auth']
ACCOUNT_ADAPTER = 'ct_django_auth.adapters.InviteOnlyAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'ct_django_auth.adapters.InviteOnlySocialAccountAdapter'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
INVITE_ONLY = env.bool('INVITE_ONLY', default=True)
# SOCIALACCOUNT_LOGIN_ON_GET stays unset (False).
```

and in the root URLconf, before `admin.site.urls`:

```python
path('', include('ct_django_auth.urls')),
path('admin/', admin.site.urls),
```

### System checks

| ID | Fails when |
|---|---|
| `ct_auth.E001` | `SOCIALACCOUNT_LOGIN_ON_GET` is true |
| `ct_auth.E002` | `ACCOUNT_ADAPTER` or `SOCIALACCOUNT_ADAPTER` is not the package's adapter or a subclass of it |
| `ct_auth.E003` | any of `SOCIALACCOUNT_QUERY_EMAIL`, `SOCIALACCOUNT_EMAIL_AUTHENTICATION`, `SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT` is not true |
| `ct_auth.E004` | `/admin/login/` does not resolve to `ct_django_auth.views.admin_login` |
| `ct_auth.W001` | a configured provider returns no email (for example `twitter_oauth2`): a new user signing in through it can never match an invite |

Errors stop `runserver`, `migrate` and the test runner, so drift fails CI.

### `admin_login`

- `DEBUG` true → Django admin's own login view (password form).
- otherwise → `302` to `reverse('account_login')`, keeping the query string, so
  `?next=` survives.

### Default templates

Plain, self-contained HTML (no `{% extends %}`: each app's base template has
different blocks). Both pages offer one action, "Back to sign in", linking to
`account_login`, and no "Sign up" link. Apps override them by placing the same
path in their own `templates/` directory.

- `account/signup_closed.html`: "Sign-up is invite-only."
- `socialaccount/authentication_error.html`: "Sign-in did not complete. The
  sign-in link expired or was already used." Served with allauth's status
  (401).

### `testing.py`

- `fake_github_api(email, verified=True)`: context manager that answers
  GitHub's token, user and emails endpoints, matched by URL, so the real
  allauth flow runs without network.
- `OAuthContractTests`: a mixin for a Django `TestCase`. The app sets
  `login_redirect_url` and implements `make_invitee(email) -> User` (which
  creates a user the app treats as fully allowed). The mixin runs the whole
  contract against the app's settings and URLconf: every row of the table in
  "Sign-in flow" below.

## Sign-in flow

| Case | Behaviour | Owner |
|---|---|---|
| Provider button | POST with CSRF to `/accounts/<provider>/login/`; a GET never starts OAuth | E001 + app template |
| Callback, `SocialAccount` already linked | Signed in | allauth |
| Callback, verified email matches exactly one user, any case | `SocialAccount` linked, signed in | adapter |
| Verified email matches two or more users differing only by case | Not linked; treated as no invite | adapter |
| Provider email not verified | Not used for matching | adapter |
| No match, `INVITE_ONLY` true | `signup_closed` page; no `User` row | adapter + template |
| No match, `INVITE_ONLY` false | New `User`; the app decides what it may see | app |
| Callback error (refresh, stale state, cancelled at provider), already signed in | Redirect to `LOGIN_REDIRECT_URL` | adapter |
| Callback error, anonymous | `authentication_error` page, 401 | template |
| `/admin/login/`, not `DEBUG` | 302 to `account_login`, `next` kept | view |
| `/admin/login/`, `DEBUG` | Admin password form | view |

Rule: **fail closed.** An uncertain match is a refusal. A missing app template
falls back to the package's, never to allauth's bare page. Redirect targets are
paths only; `next` goes through `url_has_allowed_host_and_scheme`.

## Security of a public repository

The repository is public. It must never carry:

- names, domains, IPs, email addresses or internal paths of any consuming app;
- secrets of any kind, real-looking or not, outside obviously fake fixtures.

Fixtures use `example.com` / `example.test` and the account `octo`.

Controls:

- gitleaks as a pre-commit hook and in CI; a full-history scan
  (`gitleaks git`) before the first push and before every release tag;
- CI needs no secrets: it does not publish anything;
- GitHub: `main` protected (pull request, green CI, no force-push), secret
  scanning with push protection, Dependabot alerts on;
- release tags are signed (`git tag -s vX.Y.Z`);
- commits use the GitHub no-reply address, not a personal email.

Consumers pin a commit, not a tag:

```toml
[tool.uv.sources]
ct-django-auth = { git = "https://github.com/cuongtransc/ct-django-auth", rev = "<40-char sha>" }  # v0.1.0
```

A tag can be moved; a SHA cannot. A version bump is a reviewable diff of the
SHA.

Tests cover the refusals: unverified email, ambiguous match, GET-initiated
OAuth, an off-site `next`.

## Testing

- pytest + pytest-django against a minimal project in `tests/` (settings,
  URLconf, user model = Django's).
- The real allauth GitHub flow with `fake_github_api`; no network.
- `OAuthContractTests` runs here too, against the test project, so the mixin
  itself is tested.
- A test per system check: each fires on the bad setting and stays silent on
  the good one.
- CI matrix: Python 3.12 and 3.13 × Django 6.0; ruff; gitleaks.

## Adopting the package in an app

One merge request per app:

1. Add the pinned dependency; keep the app's supply-chain policy (cool-off,
   audit).
2. Point the adapters at the package (or at app subclasses of them); add
   `ct_django_auth` to `INSTALLED_APPS`; include `ct_django_auth.urls` before
   the admin.
3. Delete the app's own copies: adapters, admin-login view, refusal tests now
   covered by the contract.
4. Add a `TestCase` that inherits `OAuthContractTests`.
5. Keep or add app overrides of the two templates.
6. Run the app's full gate and build its production image locally before
   asking for the merge.

An app that still has a password sign-in form removes it first. Before that,
every account that signs in by password needs an email that matches the
provider address it will use, or it is locked out.

## Versioning

Semantic versioning from `0.1.0`. A new system check or a stricter default is a
minor version while `0.x`; the changelog says which settings an app must
change.
