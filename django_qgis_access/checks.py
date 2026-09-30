from django.contrib.auth import get_user_model
from django.core.checks import Error
from django.db import models

from .authcfg import is_valid_prefix
from .conf import get_setting


def check_settings(app_configs, **kwargs):
    errors = []
    if not is_valid_prefix(get_setting("AUTHCFG_PREFIX")):
        errors.append(
            Error(
                "QGIS_ACCESS_AUTHCFG_PREFIX must be three alphanumeric characters.",
                hint="QGIS takes exactly seven alphanumeric characters for the id of an authentication "
                "configuration, and the last four stand for the user.",
                id="django_qgis_access.E001",
            )
        )
    if not isinstance(get_user_model()._meta.pk, models.IntegerField):
        errors.append(
            Error(
                "The primary key of the user model must be an integer.",
                hint="The id of the QGIS authentication configuration of a user is made from it.",
                id="django_qgis_access.E002",
            )
        )
    return errors
