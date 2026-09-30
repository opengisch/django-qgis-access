"""The settings of django-qgis-access, all prefixed with `QGIS_ACCESS_` in the Django settings."""

from typing import Any

from django.conf import settings

DEFAULTS: dict[str, Any] = {
    # the first three characters of the QGIS authentication configuration ids, see authcfg.py
    "AUTHCFG_PREFIX": "qgs",
    # the paths under which ApiKeyMiddleware accepts API keys
    "PATH_PREFIXES": ("/oapif/",),
    # whether the downloads take HTTP Basic credentials, from clients without a session
    "ALLOW_BASIC": False,
    # the Django template of the QGIS project, None for no project
    "PROJECT_TEMPLATE": None,
    # the base URL of the site in the project template, replaced by the URL of the server
    "PROJECT_URL_PLACEHOLDER": "http://localhost",
    # the authentication configuration id in the project template, replaced by the one of the user
    "PROJECT_AUTHCFG_PLACEHOLDER": "qgisacc",
    # the dotted path of a callable taking the request, returning more context for the project template
    "PROJECT_CONTEXT": None,
    # the name of the project file, before the user id
    "PROJECT_FILENAME": "project",
    # the URL of the server in the project, by default the one of the request
    "SERVER_URL": None,
}


def get_setting(name: str) -> Any:
    """The value of `QGIS_ACCESS_<name>`, or its default."""
    return getattr(settings, f"QGIS_ACCESS_{name}", DEFAULTS[name])
