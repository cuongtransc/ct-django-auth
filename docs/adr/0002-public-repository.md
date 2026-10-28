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
metadata. gitleaks runs before every commit, in CI, and over the full history
before the first push and every release tag. Commits use the GitHub no-reply
address. Plans that name consuming apps live in those apps' private repositories.

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
