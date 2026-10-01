import os
import subprocess
import sys
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from django_qgis_access.models import ensure_api_key

User = get_user_model()


class ApiKeyAuthTests(TestCase):
    """ApiKeyAuth in a ninja API that falls back on the session, outside the prefixes of the middleware."""

    def setUp(self):
        self.user = User.objects.create_user("alice")
        self.key = ensure_api_key(self.user).key

    def get(self, **headers):
        return self.client.get("/api/whoami", headers=headers)

    def test_bearer_authenticates(self):
        response = self.get(Authorization=f"Bearer {self.key}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"user": "alice", "auth": "alice"})

    def test_bad_keys_are_refused(self):
        inactive = User.objects.create_user("carol", is_active=False)
        for token in (uuid.uuid4(), "not-a-uuid", ensure_api_key(inactive).key):
            with self.subTest(token=token):
                self.assertEqual(self.get(Authorization=f"Bearer {token}").status_code, 401)

    def test_without_a_key_the_next_method_has_its_go(self):
        self.assertEqual(self.get().status_code, 401)
        self.client.force_login(User.objects.create_user("bob"))
        self.assertEqual(self.get().json(), {"user": "bob", "auth": "bob"})
        self.assertEqual(self.get(Authorization=f"Bearer {uuid.uuid4()}").json(), {"user": "bob", "auth": "bob"})
        self.assertEqual(self.get(Authorization=f"Bearer {self.key}").json(), {"user": "alice", "auth": "alice"})


class WithoutFrameworksTests(SimpleTestCase):
    def test_only_the_framework_auths_require_their_framework(self):
        script = """
import importlib, pkgutil, sys

sys.modules["ninja"] = None
sys.modules["rest_framework"] = None
import django

django.setup()
import django_qgis_access

optional = {"django_qgis_access.auth": "ninja", "django_qgis_access.drf": "rest_framework"}
for module in pkgutil.walk_packages(django_qgis_access.__path__, "django_qgis_access."):
    if module.name not in optional:
        importlib.import_module(module.name)
for name, framework in optional.items():
    try:
        importlib.import_module(name)
    except ImportError:
        pass
    else:
        sys.exit(f"{name} imported without {framework}")
"""
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parent.parent,
            env={**os.environ, "DJANGO_SETTINGS_MODULE": "tests.settings"},
            check=True,
        )
