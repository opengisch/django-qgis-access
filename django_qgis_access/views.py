import base64
import binascii
import functools
import re

from django.contrib.auth import authenticate
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.template import Context, Engine, TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.module_loading import import_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .authcfg import authcfg_id
from .conf import get_setting
from .models import ensure_api_key

PERMISSION = "django_qgis_access.download_qgis"
BASIC_REALM = "QGIS"

ROOT_TAG = re.compile(r"<qgis\b[^>]*>")
# the attributes of the root tag that tell who saved the project, and when
ROOT_ATTRIBUTES = {
    "saveUser": "{{ username }}",
    "saveUserFull": "{{ user.get_full_name|default:username }}",
    "saveDateTime": "{{ generation_time }}",
}


def qgis_access_required(view):
    """Let the users with the permission `download_qgis` through.

    Authenticated users without it get a 403. Anonymous requests are sent to the login page, or, with
    `QGIS_ACCESS_ALLOW_BASIC`, authenticated with HTTP Basic credentials, and get a 401 without valid ones.
    """

    @functools.wraps(view)
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


@require_safe
@never_cache
@qgis_access_required
def project(request):
    """The QGIS project of `QGIS_ACCESS_PROJECT_TEMPLATE`, made out to the user."""
    name = get_setting("PROJECT_TEMPLATE")
    if not name:
        raise Http404("There is no QGIS project.")
    template = project_template(
        name, get_setting("PROJECT_URL_PLACEHOLDER"), get_setting("PROJECT_AUTHCFG_PLACEHOLDER")
    )
    user = request.user
    context = {}
    if extra_context := get_setting("PROJECT_CONTEXT"):
        if isinstance(extra_context, str):
            extra_context = import_string(extra_context)
        context.update(extra_context(request))
    context.update({
        "authcfg": authcfg_id(user),
        "user": user,
        "user_id": user.pk,
        "username": user.get_username(),
        "generation_time": generation_time(),
        "server_url": server_url(request),
    })
    content = template.render(Context(context, autoescape=template.engine.autoescape))
    return attachment(content, f"{get_setting('PROJECT_FILENAME')}-{user.pk:04d}.qgs")


@functools.cache
def project_template(name, url_placeholder, authcfg_placeholder):
    """The project template `name`, read and prepared once.

    The placeholders become the variables `server_url` and `authcfg`, and the attributes of the root tag
    that tell who saved the project, and when, those of the download.
    """
    engine = Engine.get_default()
    source = template_source(engine, name)
    if url_placeholder:
        source = source.replace(url_placeholder, "{{ server_url }}")
    if authcfg_placeholder:
        source = source.replace(authcfg_placeholder, "{{ authcfg }}")
    source = ROOT_TAG.sub(lambda match: set_attributes(match.group(), ROOT_ATTRIBUTES), source, count=1)
    return engine.from_string(source)


def template_source(engine, name):
    """The source of the template `name`, found by the loaders of `engine`, without compiling it."""
    for loader in engine.template_loaders:
        for origin in loader.get_template_sources(name):
            try:
                return loader.get_contents(origin)
            except TemplateDoesNotExist:
                continue
    raise TemplateDoesNotExist(name)


def set_attributes(tag, attributes):
    """`tag` with `attributes` set, added if missing, its other attributes untouched."""
    for name, value in attributes.items():
        attribute = f'{name}="{value}"'
        if match := re.search(rf"(?<=\s){name}=([\"']).*?\1", tag, flags=re.DOTALL):
            tag = tag[: match.start()] + attribute + tag[match.end() :]
        else:
            tag = f"{tag[:-1]} {attribute}>"
    return tag


def generation_time():
    now = timezone.now()
    if timezone.is_aware(now):
        now = timezone.localtime(now)
    return now.strftime("%Y-%m-%dT%H:%M:%S")


def server_url(request):
    """The URL of the server, without trailing slash."""
    return (get_setting("SERVER_URL") or request.build_absolute_uri("/")).rstrip("/")
