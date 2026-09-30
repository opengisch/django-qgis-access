from ninja import NinjaAPI
from ninja.security import django_auth

from django_qgis_access.auth import ApiKeyAuth

api = NinjaAPI(urls_namespace="test_api", auth=[ApiKeyAuth(), django_auth])


@api.get("/whoami")
def whoami(request):
    return {"user": request.user.get_username(), "auth": request.auth.get_username()}
