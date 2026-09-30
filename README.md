# django-qgis-access

*django-qgis-access* hands the users of a Django site what QGIS needs to work with it: a QGIS project
pointing at the site, and a QGIS authentication file holding a personal API key. The key then
authenticates QGIS against the site's OGC API Features endpoint (e.g. [django-oapif](https://github.com/opengisch/django-oapif)).

## Installation

```sh
pip install django-qgis-access
```

Python 3.12 or later and Django 5.2 or later are required.

## Development

```sh
python -m venv .venv
.venv/bin/pip install -e '.[ninja,dev]'
.venv/bin/pre-commit install
.venv/bin/python runtests.py
```

The tests run against the small project in `tests/`, on SQLite.
