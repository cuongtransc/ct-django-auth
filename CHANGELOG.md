# Changelog

## 0.1.0 — unreleased

- Adapters: `InviteOnlyAccountAdapter` (password sign-up closed) and `InviteOnlySocialAccountAdapter` (invite-only, auto sign-up, callback errors for signed-in users, case-insensitive invite matching on verified emails that refuses any match other than exactly one user, ignores unverified `EmailAddress` rows and Unicode lookalikes).
- System checks `ct_auth.E001`-`E004` (login on GET, adapters, email settings, admin login route) and `ct_auth.W001` (provider without email).
- System check `ct_auth.E005`: `SOCIALACCOUNT_ONLY` must be true, so allauth's password, code and reset sign-in cannot bypass OAuth.
- System check `ct_auth.E006`: no provider in `SOCIALACCOUNT_PROVIDERS` may set `VERIFIED_EMAIL`.
- `admin_login` view and `ct_django_auth.urls`: staff go to OAuth outside `DEBUG`.
- Default templates for `account/signup_closed.html` and `socialaccount/authentication_error.html`.
- Contract tests: `OAuthContractTests`, `GitHubLoginMixin` and `fake_github_api` in `ct_django_auth.testing`.
