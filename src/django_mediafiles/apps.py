from pathlib import Path
from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.checks import Error, register


class DjangoMediaFiles(AppConfig):
    name = 'django_mediafiles'
    verbose_name = _("Медиафайлы")

    def ready(self):
        from . import signals

        package_path = Path(__file__).parent
        locale_path = str(package_path / "locale")
        if locale_path not in settings.LOCALE_PATHS:
            settings.LOCALE_PATHS += (locale_path,)


@register
def check_dependencies(app_configs, **kwargs):
    errors = []
    required_apps = ['django_basemodels']

    for app in required_apps:
        if app not in settings.INSTALLED_APPS:
            errors.append(
                Error(
                    f"{app} must be in INSTALLED_APPS.",
                    hint=f"Please, add '{app}' to INSTALLED_APPS",
                    id='django-mediafiles.E001',
                )
            )
    return errors
