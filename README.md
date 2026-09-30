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

## Settings

| Setting | Default | |
|---|---|---|
| `QGIS_ACCESS_AUTHCFG_PREFIX` | `"qgs"` | The first three characters of the ids of the QGIS authentication configurations, alphanumeric. |

## Security

- An API key is a permanent credential, sitting in a file on the laptop of a QGIS user. It does not expire;
  it lasts until it is revoked, by deleting it in the admin.
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
