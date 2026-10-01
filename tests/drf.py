from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_qgis_access.drf import ApiKeyAuthentication

from .views import username


@api_view(["GET", "POST"])
@authentication_classes([ApiKeyAuthentication, SessionAuthentication])
@permission_classes([AllowAny])
def whoami(request):
    """The name of the user of the request, and the authentication class that let it in."""
    authenticator = request.successful_authenticator
    return Response({"user": username(request.user), "by": type(authenticator).__name__ if authenticator else None})
