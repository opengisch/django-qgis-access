import base64
import binascii
from functools import wraps

from django.contrib.auth import authenticate
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .authcfg import authcfg_id
from .conf import get_setting
from .models import ensure_api_key

PERMISSION = "django_qgis_access.download_qgis"
BASIC_REALM = "QGIS"


def qgis_access_required(view):
    """Let the users with the permission `download_qgis` through.

    Authenticated users without it get a 403. Anonymous requests are sent to the login page, or, with
    `QGIS_ACCESS_ALLOW_BASIC`, authenticated with HTTP Basic credentials, and get a 401 without valid ones.
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if not get_setting("ALLOW_BASIC"):
                return redirect_to_login(request.get_full_path())
            user = basic_auth_user(request)
            if user is None:
                return basic_auth_challenge()
            request.user = user
        if not request.user.has_perm(PERMISSION):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def basic_auth_user(request):
    """The user of the HTTP Basic credentials of the request, checked by the authentication backends."""
    scheme, _, credentials = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "basic":
        return None
    try:
        decoded = base64.b64decode(credentials.strip(), validate=True).decode()
    except (binascii.Error, UnicodeDecodeError):
        return None
    username, colon, password = decoded.partition(":")
    if not colon:
        return None
    return authenticate(request, username=username, password=password)


def basic_auth_challenge():
    response = HttpResponse(status=401)
    response["WWW-Authenticate"] = f'Basic realm="{BASIC_REALM}", charset="UTF-8"'
    return response


def attachment(content, filename):
    response = HttpResponse(content, content_type="application/xml")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_safe
@never_cache
@qgis_access_required
def auth_xml(request):
    """The QGIS authentication configuration of the user, with their API key, minted if need be."""
    user = request.user
    context = {
        "api_key": ensure_api_key(user).key,
        "authcfg": authcfg_id(user),
    }
    return attachment(render_to_string("django_qgis_access/auth.xml", context), f"auth-{user.pk:04d}.xml")
