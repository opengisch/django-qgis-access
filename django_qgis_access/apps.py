from django.apps import AppConfig
from django.core import checks
from django.utils.translation import gettext_lazy as _


class QgisAccessConfig(AppConfig):
    name = "django_qgis_access"
    verbose_name = _("QGIS access")

    def ready(self):
        from .checks import check_settings

        checks.register(check_settings)
