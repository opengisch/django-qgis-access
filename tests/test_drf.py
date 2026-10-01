import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from django_qgis_access.models import ensure_api_key

User = get_user_model()
URL = "/drf/whoami"


class ApiKeyAuthenticationTests(TestCase):
    """ApiKeyAuthentication in a DRF view that falls back on the session, outside the prefixes of the middleware."""

    def setUp(self):
        self.user = User.objects.create_user("alice")
        self.key = ensure_api_key(self.user).key

    def get(self, **headers):
        return self.client.get(URL, headers=headers)

    def test_key_authenticates(self):
        for scheme in ("Bearer", "bearer"):
            with self.subTest(scheme=scheme):
                response = self.get(Authorization=f"{scheme} {self.key}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"user": "alice", "by": "ApiKeyAuthentication"})

    def test_without_key_the_session_has_its_go(self):
        self.client.force_login(User.objects.create_user("bob"))
        self.assertEqual(self.get().json(), {"user": "bob", "by": "SessionAuthentication"})

    def test_without_credentials_the_request_is_anonymous(self):
        self.assertEqual(self.get().json(), {"user": "anonymous", "by": None})

    def test_other_schemes_are_left_alone(self):
        self.assertEqual(self.get(Authorization="Basic Ym9iOnNlY3JldA==").json(), {"user": "anonymous", "by": None})

    def test_bad_keys_are_refused(self):
        inactive = User.objects.create_user("carol", is_active=False)
        for token in (uuid.uuid4(), "not-a-uuid", "", ensure_api_key(inactive).key):
            with self.subTest(token=token):
                response = self.get(Authorization=f"Bearer {token}")
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["WWW-Authenticate"], "Bearer")

    def test_revoked_key_is_refused(self):
        self.user.api_keys.all().delete()
        self.assertEqual(self.get(Authorization=f"Bearer {self.key}").status_code, 401)

    def test_key_needs_no_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(URL, headers={"Authorization": f"Bearer {self.key}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["by"], "ApiKeyAuthentication")

    def test_session_keeps_the_csrf_check(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(URL).status_code, 403)
