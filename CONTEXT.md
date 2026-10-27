# ct-django-auth

The sign-in layer shared by Django apps that admit only invited people, through
OAuth only.

## Language

**Invite**:
A user account an admin creates with the email of the person allowed in; that
person's first OAuth sign-in with the same verified email claims it.
_Avoid_: member (apps use it for their own access levels), approval

**Invitee**:
The person an Invite is for, before and after they first sign in.

**Invite-only mode**:
The state in which an OAuth sign-in that matches no Invite is refused and
creates no account.
_Avoid_: closed beta, whitelist

**Open sign-up**:
The opposite of Invite-only mode: an unmatched OAuth sign-in creates a new
account, and the app decides what it may see.

**Dead-end page**:
A page that ends a sign-in attempt without signing anyone in: sign-up closed,
or a failed provider callback. It offers one way back, to sign in.

**Policy drift**:
An app's settings disagreeing with the shared sign-in policy, such as allowing a
sign-in to start from a plain link.
