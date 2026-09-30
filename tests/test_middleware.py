import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from django_qgis_access.models import ensure_api_key

User = get_user_model()


class ApiKeyMiddlewareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice")
        self.key = ensure_api_key(self.user).key
        self.client = Client(enforce_csrf_checks=True)

    def bearer(self, token):
        return {"Authorization": f"Bearer {token}"}

    def assertUser(self, response, username):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), username)

    def test_bearer_authenticates_under_the_prefix(self):
        self.assertUser(self.client.get("/oapif/whoami", headers=self.bearer(self.key)), "alice")

    def test_scheme_is_case_insensitive(self):
        self.assertUser(self.client.get("/oapif/whoami", headers={"Authorization": f"bearer {self.key}"}), "alice")

    def test_async_views_get_the_user(self):
        self.assertUser(self.client.get("/oapif/async-whoami", headers=self.bearer(self.key)), "alice")

    def test_bearer_replaces_the_session(self):
        self.client.force_login(User.objects.create_user("bob"))
        self.assertUser(self.client.get("/oapif/whoami"), "bob")
        self.assertUser(self.client.get("/oapif/whoami", headers=self.bearer(self.key)), "alice")

    def test_bearer_is_ignored_outside_the_prefix(self):
        self.assertUser(self.client.get("/other/whoami", headers=self.bearer(self.key)), "anonymous")

    @override_settings(QGIS_ACCESS_PATH_PREFIXES=["/other/"])
    def test_prefixes_setting(self):
        self.assertUser(self.client.get("/other/whoami", headers=self.bearer(self.key)), "alice")
        self.assertUser(self.client.get("/oapif/whoami", headers=self.bearer(self.key)), "anonymous")

    @override_settings(QGIS_ACCESS_PATH_PREFIXES="/other/")
    def test_a_single_prefix(self):
        self.assertUser(self.client.get("/other/whoami", headers=self.bearer(self.key)), "alice")
        self.assertUser(self.client.get("/oapif/whoami", headers=self.bearer(self.key)), "anonymous")

    def test_bad_keys_leave_the_request_anonymous(self):
        inactive = User.objects.create_user("carol", is_active=False)
        for token in (uuid.uuid4(), "not-a-uuid", "", "  ", ensure_api_key(inactive).key):
            with self.subTest(token=token):
                self.assertUser(self.client.get("/oapif/whoami", headers=self.bearer(token)), "anonymous")

    def test_other_schemes_are_ignored(self):
        for header in (f"Basic {self.key}", str(self.key), f"Token {self.key}"):
            with self.subTest(header=header):
                response = self.client.get("/oapif/whoami", headers={"Authorization": header})
                self.assertUser(response, "anonymous")

    def test_bearer_skips_the_csrf_check(self):
        self.assertUser(self.client.post("/oapif/whoami", headers=self.bearer(self.key)), "alice")

    def test_session_keeps_the_csrf_check(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post("/oapif/whoami").status_code, 403)

    def test_bad_keys_keep_the_csrf_check(self):
        self.client.force_login(self.user)
        for token in (uuid.uuid4(), "not-a-uuid"):
            with self.subTest(token=token):
                self.assertEqual(self.client.post("/oapif/whoami", headers=self.bearer(token)).status_code, 403)

    def test_csrf_check_outside_the_prefix(self):
        self.assertEqual(self.client.post("/other/whoami", headers=self.bearer(self.key)).status_code, 403)
