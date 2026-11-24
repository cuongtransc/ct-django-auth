# 0002: Publish the package as a public GitHub repository, accepting that nothing about its consumers may appear in it

> Status: Accepted · Date: 2026-10-27

## Context

The apps that use this package are private and are built into Docker images on a
CI runner. Installing a private dependency at build time needs a credential in
every app's CI and Dockerfile.

Source: [design spec](../superpowers/specs/2026-10-27-ct-django-auth-design.md)

## Decision

The repository is public on GitHub, and apps install it from git.

A public repository needs no build-time credential in any app; the code holds no
secret and no business logic, only a generic sign-in policy.

## Consequences

Everything committed is published: no consumer names, domains, IPs, emails,
internal paths or real-looking secrets, in code, fixtures, docs or commit
metadata. The secret scanner runs before every commit, in CI, and over the full
history before the first push and every release tag. Commits use the GitHub
no-reply address. Plans that name consuming apps live in those apps' private
repositories.

### 2026-11-24: the secret scanner is betterleaks

The scanner is betterleaks 1.10.1, not gitleaks. It takes gitleaks' command line,
its TOML config and its JSON, and it is the only scanner the owner's machines
carry, so one scanner covers every repository instead of two. The decision above
is unchanged: the scan runs before every commit, in CI, and over the full history
before the first push and every release tag.

`.gitleaks.toml` keeps its name because that is the file betterleaks reads, is
read only when a scan passes `--config .gitleaks.toml` (the mise tasks, the
pre-commit hook and CI all do), and keeps the built-in rules. It adds one
exception: betterleaks' `generic-password` rule flags the obviously fake fixture
password the package's own contract tests sign in with, in
`ct_django_auth/testing.py` and in the plan that quotes it, so that one rule
allows that one password in those two files. Every other rule still scans them,
and `generic-password` still fires in every other file.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| Private repository on the apps' git host, installed from git | Every app's CI and Dockerfile would need a deploy token to clone it. |
| Private package registry | Needs a token at build time and a release pipeline; more machinery than three consumers justify. |
| Vendored copy in each app with a drift check | A fix still lands as one commit per app, the cost the package exists to remove. |

## Updates

### 2026-10-28: web-UI merges carry the owner's email

Merges done in the GitHub web UI record the owner's account email, not the
no-reply address. The owner accepts this: the address was already public.
Commits made from a local clone still use the no-reply address.
