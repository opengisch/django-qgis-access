"""The settings of django-qgis-access, all prefixed with `QGIS_ACCESS_` in the Django settings."""

from typing import Any

from django.conf import settings

DEFAULTS: dict[str, Any] = {
    # the first three characters of the QGIS authentication configuration ids, see authcfg.py
    "AUTHCFG_PREFIX": "qgs",
}


def get_setting(name: str) -> Any:
    """The value of `QGIS_ACCESS_<name>`, or its default."""
    return getattr(settings, f"QGIS_ACCESS_{name}", DEFAULTS[name])
