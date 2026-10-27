# Changelog

## 0.1.0 — unreleased

- Adapters: `InviteOnlyAccountAdapter` (password sign-up closed) and `InviteOnlySocialAccountAdapter` (invite-only, auto sign-up, callback errors for signed-in users, case-insensitive invite matching on verified emails).
- System checks `ct_auth.E001`-`E004` (login on GET, adapters, email settings, admin login route) and `ct_auth.W001` (provider without email).
- `admin_login` view and `ct_django_auth.urls`: staff go to OAuth outside `DEBUG`.
- Default templates for `account/signup_closed.html` and `socialaccount/authentication_error.html`.
- Contract tests: `OAuthContractTests`, `GitHubLoginMixin` and `fake_github_api` in `ct_django_auth.testing`.
