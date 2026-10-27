from django.apps import apps

import ct_django_auth


def test_version():
    assert ct_django_auth.__version__ == '0.1.0'


def test_app_is_installed_in_test_project():
    assert apps.get_app_config('ct_django_auth').name == 'ct_django_auth'
