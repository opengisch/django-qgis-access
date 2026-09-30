import base64
import xml.etree.ElementTree as ET

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from django_qgis_access.models import ApiKey

User = get_user_model()

URL = "/qgis/auth.xml"


def basic(username, password):
    return {"Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()}


class QgisUserMixin:
    def setUp(self):
        self.user = User.objects.create_user("alice", password="secret", id=42)
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="django_qgis_access", codename="download_qgis")
        )


class AuthXmlTests(QgisUserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def config(self, response):
        root = ET.fromstring(response.content)
        self.assertEqual(root.tag, "qgis_authentication")
        (config,) = root.findall("configurations/AuthMethodConfig")
        return config

    def test_url(self):
        self.assertEqual(reverse("qgis_access:auth_xml"), URL)

    def test_download(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="auth-0042.xml"')
        self.assertIn("no-store", response["Cache-Control"])

        config = self.config(response)
        self.assertEqual(config.get("id"), "qgs0042")
        self.assertEqual(config.get("name"), "qgs0042")
        self.assertEqual(config.get("method"), "APIHeader")
        api_key = ApiKey.objects.get()
        self.assertEqual(api_key.user, self.user)
        self.assertEqual(config.find("Config").get("Authorization"), f"Bearer {api_key.key}")

    def test_key_is_minted_once(self):
        first = self.config(self.client.get(URL)).find("Config").get("Authorization")
        second = self.config(self.client.get(URL)).find("Config").get("Authorization")
        self.assertEqual(first, second)
        self.assertEqual(ApiKey.objects.count(), 1)

    def test_existing_key_is_handed_out(self):
        api_key = ApiKey.objects.create(user=self.user)
        self.assertEqual(self.config(self.client.get(URL)).find("Config").get("Authorization"), f"Bearer {api_key.key}")

    @override_settings(QGIS_ACCESS_AUTHCFG_PREFIX="dwb")
    def test_prefix(self):
        self.assertEqual(self.config(self.client.get(URL)).get("id"), "dwb0042")

    def test_large_user_id(self):
        user = User.objects.create_superuser("bob", id=10036)
        self.client.force_login(user)
        response = self.client.get(URL)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="auth-10036.xml"')
        self.assertEqual(self.config(response).get("id"), "qgsa010")

    def test_only_get(self):
        self.assertEqual(self.client.post(URL).status_code, 405)


class AccessTests(QgisUserMixin, TestCase):
    def test_permission_is_required(self):
        self.client.force_login(User.objects.create_user("bob"))
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertFalse(ApiKey.objects.exists())

    def test_superusers_pass(self):
        self.client.force_login(User.objects.create_superuser("root"))
        self.assertEqual(self.client.get(URL).status_code, 200)

    def test_anonymous_requests_go_to_the_login_page(self):
        response = self.client.get(URL)
        self.assertRedirects(response, f"/accounts/login/?next={URL}", fetch_redirect_response=False)
        self.assertFalse(ApiKey.objects.exists())

    def test_basic_is_off_by_default(self):
        response = self.client.get(URL, headers=basic("alice", "secret"))
        self.assertRedirects(response, f"/accounts/login/?next={URL}", fetch_redirect_response=False)
        self.assertFalse(ApiKey.objects.exists())


@override_settings(QGIS_ACCESS_ALLOW_BASIC=True)
class BasicTests(QgisUserMixin, TestCase):
    def assertChallenge(self, response):
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], 'Basic realm="QGIS", charset="UTF-8"')
        self.assertFalse(ApiKey.objects.exists())

    def test_basic_credentials(self):
        response = self.client.get(URL, headers=basic("alice", "secret"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ApiKey.objects.get().user, self.user)

    def test_no_session_is_opened(self):
        self.client.get(URL, headers=basic("alice", "secret"))
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_missing_credentials(self):
        self.assertChallenge(self.client.get(URL))

    def test_wrong_password(self):
        self.assertChallenge(self.client.get(URL, headers=basic("alice", "wrong")))

    def test_unknown_user(self):
        self.assertChallenge(self.client.get(URL, headers=basic("nobody", "secret")))

    def test_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        self.assertChallenge(self.client.get(URL, headers=basic("alice", "secret")))

    def test_malformed_credentials(self):
        for header in ("Basic", "Basic !!!", "Basic " + base64.b64encode(b"alice").decode(), "Bearer secret"):
            with self.subTest(header=header):
                self.assertChallenge(self.client.get(URL, headers={"Authorization": header}))

    def test_permission_is_required(self):
        User.objects.create_user("bob", password="secret")
        self.assertEqual(self.client.get(URL, headers=basic("bob", "secret")).status_code, 403)

    def test_session_needs_no_credentials(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(URL).status_code, 200)
