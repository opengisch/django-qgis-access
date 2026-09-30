from .conf import get_setting
from .models import user_for_api_key


class ApiKeyMiddleware:
    """Bearer token auth for OAPIF, and only there.

    A key is a permanent credential sitting in a file on a QGIS user's laptop.
    Accepted sitewide it would be a login without password or second factor,
    leaving the MFA policy to whoever copies an auth.xml. So the key is only
    accepted under the paths of `QGIS_ACCESS_PATH_PREFIXES` (default `/oapif/`),
    matched against `request.path_info`; elsewhere, the session stays in charge.

    A request with a valid key (`Authorization: Bearer <key>`) of an active user
    is that user's, and skips the CSRF check: a browser never sends the key on its
    own, so a forged request cannot carry it. Every other request, cookie sessions
    included, keeps the full CSRF protection.

    List it after `django.contrib.auth.middleware.AuthenticationMiddleware`, whose
    user it replaces.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.authenticate(request)
        return self.get_response(request)

    def authenticate(self, request):
        prefixes = get_setting("PATH_PREFIXES")
        if isinstance(prefixes, str):
            prefixes = (prefixes,)
        if not request.path_info.startswith(tuple(prefixes)):
            return

        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        token = token.strip()
        if scheme.lower() != "bearer" or not token:
            return

        user = user_for_api_key(token)
        if user is None:
            return

        async def auser():
            return user

        request.user = user
        request.auser = auser
        request._dont_enforce_csrf_checks = True
