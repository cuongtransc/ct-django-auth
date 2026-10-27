from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse


def admin_login(request, extra_context=None):
    """Send staff to OAuth sign-in; keep the admin password form under DEBUG."""
    if settings.DEBUG:
        return admin.site.login(request, extra_context)
    query = request.META.get('QUERY_STRING')
    return HttpResponseRedirect(
        reverse('account_login') + ('?' + query if query else '')
    )
