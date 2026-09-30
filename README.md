# django-qgis-access

*django-qgis-access* hands the users of a Django site what QGIS needs to work with it: a QGIS project
pointing at the site, and a QGIS authentication file holding a personal API key. The key then
authenticates QGIS against the site's OGC API Features endpoint (e.g. [django-oapif](https://github.com/opengisch/django-oapif)).

## Installation

```sh
pip install django-qgis-access
```

Python 3.12 or later and Django 5.2 or later are required.

Add the app and create its table:

```python
INSTALLED_APPS = [
    ...
    "django_qgis_access",
]
```

```sh
python manage.py migrate django_qgis_access
```

## API keys

An `ApiKey` (`django_qgis_access.models.ApiKey`) belongs to a user (`user.api_keys`); its `key`, a random
UUID, is the token. It is not the primary key, which forms and URLs carry. Keys are issued, never entered: `ensure_api_key(user)` returns the key of
a user and mints one the first time. The permission `django_qgis_access.download_qgis` ("Can download the
QGIS project and auth file") stands for "works with QGIS"; grant it to the groups that do.

Each user gets a QGIS authentication configuration of their own, whose id is `authcfg_id(user)`
(`django_qgis_access.authcfg`). QGIS takes exactly seven alphanumeric characters for such an id: the three
of `QGIS_ACCESS_AUTHCFG_PREFIX`, then four for the user id, zero-padded: user 42 gets `qgs0042`. User ids
from 10000 on are a lowercase letter followed by three base-36 digits (user 10000 gets `qgsa000`, 10036
`qgsa010`), so that no two users share an id and existing ids never change. That makes room for user ids up
to 1 223 055; a larger one raises a `ValueError`. A system check makes sure that the prefix is three
alphanumeric characters (`django_qgis_access.E001`) and that the user model has an integer primary key
(`django_qgis_access.E002`).

### Admin

The app registers nothing in the admin. Its inline lists the keys of a user on the user form, where deleting
a key revokes it (its owner gets a fresh one with the next download). It shows the last four characters of
a key, and offers no way to add one: keys are minted by the download. A key acts as its owner, so the keys
of superusers are only listed to superusers.

```python
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django_qgis_access.admin import ApiKeyInline


class UserAdmin(BaseUserAdmin):
    inlines = [*BaseUserAdmin.inlines, ApiKeyInline]
```

With [Unfold](https://github.com/unfoldadmin/django-unfold), combine the mixin with its inline class:

```python
from django_qgis_access.admin import ApiKeyInlineMixin
from unfold.admin import TabularInline


class ApiKeyInline(ApiKeyInlineMixin, TabularInline):
    pass
```

The inline follows the permissions of the `ApiKey` model: seeing keys takes `view_apikey`, revoking them
`delete_apikey`.

## Downloads

```python
urlpatterns = [
    ...
    path("qgis/", include("django_qgis_access.urls")),
]
```

| URL name | Path | |
|---|---|---|
| `qgis_access:auth_xml` | `auth.xml` | The QGIS authentication file of the user. |
| `qgis_access:project` | `project.qgs` | The QGIS project, made out to the user. |

### The auth file

The authentication file, `auth-0042.xml` for user 42, holds one configuration of the `APIHeader` method,
with `authcfg_id(user)` as id and name, which sends `Authorization: Bearer <key>`. Downloading it mints the
key of the user if they have none yet, so only those allowed to download ever hold one. QGIS imports it in
its options: *Authentication*, *Utilities*, *Import Authentication Configurations from File*.

### The project

The project is a Django template, `QGIS_ACCESS_PROJECT_TEMPLATE` (without one, `project.qgs` is a 404): a
`.qgs` file saved by QGIS, connected to the site at `QGIS_ACCESS_PROJECT_URL_PLACEHOLDER` (e.g. a
development server at `http://localhost:8000`) through the authentication configuration
`QGIS_ACCESS_PROJECT_AUTHCFG_PLACEHOLDER` (seven alphanumeric characters, `qgisacc` by default). The
download, `project-0042.qgs` for user 42, has

- the URL placeholder replaced by the URL of the server: `QGIS_ACCESS_SERVER_URL`, or the one of the request
  (`request.build_absolute_uri("/")`), without trailing slash;
- the authcfg placeholder replaced by `authcfg_id(user)`, the id of the configuration of the auth file;
- the attributes `saveUser`, `saveUserFull` and `saveDateTime` of the root tag `<qgis>` set to the username,
  the full name of the user and the time of the download; the others, such as `version`, stay as they are;
- the template rendered with the context `authcfg`, `user`, `user_id`, `username`, `generation_time` and
  `server_url`, to which `QGIS_ACCESS_PROJECT_CONTEXT`, the dotted path of a callable taking the request,
  adds a dictionary of its own (its keys do not override those above). Project variables, for one, can
  take values from it: `<value type="QString">{{ user_id }}</value>`.

The replacements are plain text, so choose placeholders that appear nowhere else in the project. Should the
project contain `{{`, `{%` or `{#` of its own, wrap them in `{% verbatim %}`. The template is read and
prepared once per process: restart the server after changing it.

### Access

The downloads take the permission `django_qgis_access.download_qgis`:

- an authenticated user without it gets a 403;
- an anonymous request is sent to the login page (`LOGIN_URL`), or, with `QGIS_ACCESS_ALLOW_BASIC`,
  authenticated with HTTP Basic credentials, checked by the authentication backends of Django. Missing or
  wrong credentials get a 401 with `WWW-Authenticate: Basic realm="QGIS"`. This is meant for clients such
  as a QGIS plugin, which exchange a username and password once for the auth file, then use the key. No
  session is opened.

The downloads answer GET and HEAD only, and are never cached (`Cache-Control: no-store`). The decorator
that guards them, `django_qgis_access.views.qgis_access_required`, is there for views of your own.

## Authenticating with API keys

QGIS sends the key as `Authorization: Bearer <key>`. Two ways to accept it:

**In a django-ninja API**, such as the `OAPIF` of django-oapif, with the `ninja` extra
(`pip install 'django-qgis-access[ninja]'`):

```python
from django_oapif.auth import BasicAuth, DjangoAuth
from django_oapif import OAPIF
from django_qgis_access.auth import ApiKeyAuth

api = OAPIF(auth=[ApiKeyAuth(), BasicAuth(), DjangoAuth()])
```

`ApiKeyAuth` returns the active user holding the key and makes it `request.user`. Without a key, or with a
bad one, the next method has its go. It needs no CSRF exemption: django-ninja checks CSRF only for cookie
authentication.

**For any view**, with the middleware, listed after Django's `AuthenticationMiddleware`, whose user it
replaces:

```python
MIDDLEWARE = [
    ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_qgis_access.middleware.ApiKeyMiddleware",
    ...
]
```

It accepts keys only under the paths of `QGIS_ACCESS_PATH_PREFIXES` (by default `/oapif/`, matched against
`request.path_info`). A request with the valid key of an active user becomes that user's (`request.user`
and `request.auser()`), and skips the CSRF check; every other request, cookie sessions included, keeps it.

Only `django_qgis_access.auth` needs django-ninja; the rest of the package imports without it.

## Settings

| Setting | Default | |
|---|---|---|
| `QGIS_ACCESS_AUTHCFG_PREFIX` | `"qgs"` | The first three characters of the ids of the QGIS authentication configurations, alphanumeric. |
| `QGIS_ACCESS_PATH_PREFIXES` | `("/oapif/",)` | The paths under which `ApiKeyMiddleware` accepts API keys. |
| `QGIS_ACCESS_ALLOW_BASIC` | `False` | Whether the downloads take HTTP Basic credentials from requests without a session. |
| `QGIS_ACCESS_PROJECT_TEMPLATE` | `None` | The name of the Django template of the QGIS project. |
| `QGIS_ACCESS_PROJECT_URL_PLACEHOLDER` | `"http://localhost"` | The URL in the project template that stands for the server. |
| `QGIS_ACCESS_PROJECT_AUTHCFG_PLACEHOLDER` | `"qgisacc"` | The authentication configuration id in the project template that stands for the one of the user. |
| `QGIS_ACCESS_SERVER_URL` | `None` | The URL of the server in the project, e.g. `"https://example.com"`; by default the one of the request. |
| `QGIS_ACCESS_PROJECT_CONTEXT` | `None` | The dotted path of a callable taking the request and returning more context for the project template. |
| `QGIS_ACCESS_PROJECT_FILENAME` | `"project"` | The name of the project file, before the user id: `project-0042.qgs`. |

## Security

- An API key is a permanent credential, sitting in a file on the laptop of a QGIS user. It does not expire;
  it lasts until it is revoked, by deleting it in the admin.
- Keep Bearer authentication to the OGC API Features endpoint, as the middleware does by default. Accepted
  sitewide, a key would be a login without password or second factor, leaving a policy of multi-factor
  authentication to whoever copies an auth file. Scoped this way, a leaked key costs what a QGIS session
  costs, and the admin falls back on the session.
- Keys are issued, never entered, and only to users with the permission `download_qgis`: downloading the
  auth file is what mints them.
- Leave `QGIS_ACCESS_ALLOW_BASIC` off where logins require a second factor (TOTP with django-allauth, say):
  HTTP Basic takes a password alone, and would hand out a key, a permanent credential, for it.
- The admin never shows a whole key: its inline shows the last four characters, and its form carries the
  primary key of the rows, never their keys. Only superusers see the keys of superusers, as a key acts as
  its owner.

## Development

```sh
python -m venv .venv
.venv/bin/pip install -e '.[ninja,dev]'
.venv/bin/pre-commit install
.venv/bin/python runtests.py
```

The tests run against the small project in `tests/`, on SQLite.
