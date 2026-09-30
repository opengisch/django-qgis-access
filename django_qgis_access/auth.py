"""Authentication with API keys for django-ninja APIs, which requires the `ninja` extra.

The rest of the package does without django-ninja: `ApiKeyMiddleware`, in `django_qgis_access.middleware`,
does the same for any view.
"""

from typing import Any

from django.http import HttpRequest
from ninja.security import HttpBearer

from .models import user_for_api_key


class ApiKeyAuth(HttpBearer):
    """Bearer authentication with an API key (`Authorization: Bearer <key>`).

    Returns the active user holding the key, and makes it `request.user`. Without a key, or with an unknown
    one, it returns None, and the next authentication method has its go, as in django-oapif:

        OAPIF(auth=[ApiKeyAuth(), BasicAuth(), DjangoAuth()])
    """

    def authenticate(self, request: HttpRequest, token: str) -> Any | None:
        user = user_for_api_key(token.strip())
        if user is not None:
            request.user = user
        return user
