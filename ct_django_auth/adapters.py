from allauth.account import app_settings as account_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


def invite_only_enabled() -> bool:
    return getattr(settings, 'INVITE_ONLY', True) is not False


class InviteOnlyAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request) -> bool:
        return False


class InviteOnlySocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin) -> bool:
        return not invite_only_enabled()

    def is_auto_signup_allowed(self, request, sociallogin) -> bool:
        return True

    def on_authentication_error(
        self, request, provider, error=None, exception=None, extra_context=None
    ) -> None:
        if request.user.is_authenticated:
            raise ImmediateHttpResponse(redirect(settings.LOGIN_REDIRECT_URL))

    def invite_candidates(self, email):
        """Yield ``(user, stored_address)`` for every user that may own ``email``.

        The database match is case-insensitive and may fold Unicode lookalikes
        (Postgres ``UPPER``); ``authenticate_by_email`` filters the stored value
        exactly. allauth ``EmailAddress`` rows count only when verified.
        """
        from allauth.account.models import EmailAddress

        field = account_settings.USER_MODEL_EMAIL_FIELD
        if field:
            lookup = {f'{field}__iexact': email}
            for user in get_user_model().objects.filter(**lookup):
                yield user, getattr(user, field) or ''
        rows = EmailAddress.objects.filter(email__iexact=email, verified=True)
        for row in rows.select_related('user'):
            yield row.user, row.email

    def authenticate_by_email(self, sociallogin):
        """Return ``(user, email)`` only when the provider's verified addresses
        point at exactly one user; anything else is a refusal (fail closed)."""
        users = {}
        matched = None
        for address in sociallogin.email_addresses:
            if not address.verified or not address.email:
                continue
            if not self.can_authenticate_by_email(sociallogin, address.email):
                continue
            wanted = address.email.lower()
            for user, stored in self.invite_candidates(address.email):
                if stored.lower() == wanted:
                    users[user.pk] = user
                    matched = matched or address.email
        if len(users) != 1:
            return None
        return next(iter(users.values())), matched
