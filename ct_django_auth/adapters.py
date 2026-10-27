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

    def authenticate_by_email(self, sociallogin):
        found = super().authenticate_by_email(sociallogin)
        if found:
            return found
        for address in sociallogin.email_addresses:
            if not address.verified:
                continue
            if not self.can_authenticate_by_email(sociallogin, address.email):
                continue
            users = get_user_model().objects.filter(email__iexact=address.email)[:2]
            if len(users) == 1:
                return users[0], address.email
        return None
