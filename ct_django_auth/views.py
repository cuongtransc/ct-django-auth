from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url


def admin_login(request, extra_context=None):
    """Send staff to the app's sign-in page (LOGIN_URL); keep the admin password
    form under DEBUG."""
    if settings.DEBUG:
        return admin.site.login(request, extra_context)
    query = request.META.get('QUERY_STRING')
    return HttpResponseRedirect(
        resolve_url(settings.LOGIN_URL) + ('?' + query if query else '')
    )
