# 0001: Apps keep their auth settings explicit; the package enforces them with system checks, at the cost of ~8 repeated lines per app

> Status: Accepted · Date: 2026-10-27

## Context

The package must stop apps drifting from the shared sign-in policy. One app had
already enabled GET-initiated OAuth while the others refused it, unnoticed until
a review. Settings live in each app's `settings.py`, which the package does not
own.

Source: [design spec](../superpowers/specs/2026-10-27-ct-django-auth-design.md)

## Decision

Each app writes its allauth settings itself. The package registers Django system
checks (`ct_auth.E001`..`E004`) that raise an error when a setting breaks the
policy, so `manage.py check`, `migrate` and the test run fail in the app's CI.

This beats a helper that writes the settings for the app: reading the app's
`settings.py` still shows what is in force, and drift is caught where it happens
instead of being hidden behind a call.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| `configure(globals())` writes every allauth setting | Fewer lines, but the settings file no longer shows what is in force, and a renamed allauth setting would fail silently inside the helper. |
| Adapters only, settings described in the README | Nothing stops drift; this is the situation that produced the GET-initiated OAuth incident. |
