"""Authentication with API keys for Django REST framework APIs, which requires the `drf` extra.

The rest of the package does without Django REST framework.
"""

from rest_framework import authentication, exceptions

from .models import user_for_api_key


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Bearer authentication with an API key (`Authorization: Bearer <key>`).

    Authenticates the active user holding the key. Without a Bearer key, the next authentication class has its
    go. A bad key, malformed, unknown, revoked or of an inactive user, is refused with a 401, as Django REST
    framework's own `TokenAuthentication` does:

        REST_FRAMEWORK = {
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "django_qgis_access.drf.ApiKeyAuthentication",
                "rest_framework.authentication.SessionAuthentication",
            ],
        }
    """

    keyword = "Bearer"

    def authenticate(self, request):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != self.keyword.lower():
            return None
        user = user_for_api_key(token.strip())
        if user is None:
            raise exceptions.AuthenticationFailed("Invalid API key.")
        return (user, None)

    def authenticate_header(self, request):
        return self.keyword
