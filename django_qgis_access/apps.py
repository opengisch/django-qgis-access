from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class QgisAccessConfig(AppConfig):
    name = "django_qgis_access"
    verbose_name = _("QGIS access")
