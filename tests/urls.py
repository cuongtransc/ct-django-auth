from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path('', include('ct_django_auth.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('home/', views.home, name='home'),
]
