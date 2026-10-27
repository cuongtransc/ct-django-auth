# 0003: Consumers pin a commit SHA, not a tag, accepting a less readable dependency line

> Status: Accepted · Date: 2026-10-27

## Context

The package controls who may sign in to every app that uses it, and it is
installed from a public git repository. A git tag can be deleted and recreated
on another commit; whoever controls the repository, or an account that
compromises it, can change what an app installs without the app changing a
line.

Source: [design spec](../superpowers/specs/2026-10-27-ct-django-auth-design.md)

## Decision

Apps declare the dependency with `rev = "<40-character SHA>"` and a trailing
comment naming the version. Release tags are signed, but they are labels for
humans, not what apps resolve.

A SHA cannot be moved, so an app installs exactly the code it reviewed, and
every upgrade is a visible diff in a merge request.

## Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| `tag = "vX.Y.Z"` | Readable, but a moved tag silently changes what the next image build installs. |
| `branch = "main"` | Every build could pull unreviewed code into the sign-in path. |
