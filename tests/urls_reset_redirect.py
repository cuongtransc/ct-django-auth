from django.urls import path
from django.views.generic import RedirectView

from .urls import urlpatterns as base_urlpatterns

urlpatterns = [
    path('accounts/password/reset/', RedirectView.as_view(url='/accounts/login/')),
    *base_urlpatterns,
]
