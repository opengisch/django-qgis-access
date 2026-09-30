import datetime
import xml.etree.ElementTree as ET
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from django_qgis_access.views import project_template

User = get_user_model()

URL = "/qgis/project.qgs"
NOW = datetime.datetime(2026, 9, 30, 10, 0, tzinfo=datetime.UTC)


@override_settings(QGIS_ACCESS_PROJECT_TEMPLATE="project.qgs")
@mock.patch("django.utils.timezone.now", return_value=NOW)
class ProjectTests(TestCase):
    def setUp(self):
        project_template.cache_clear()
        self.user = User.objects.create_user("alice", id=42, first_name="Alice", last_name="Liddell")
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="django_qgis_access", codename="download_qgis")
        )
        self.client.force_login(self.user)

    def get(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        return response

    def project(self):
        return ET.fromstring(self.get().content)

    def variables(self, project):
        names = [value.text for value in project.findall("properties/Variables/variableNames/value")]
        values = [value.text for value in project.findall("properties/Variables/variableValues/value")]
        return dict(zip(names, values, strict=True))

    def test_url(self, now):
        self.assertEqual(reverse("qgis_access:project"), URL)

    def test_download(self, now):
        response = self.get()
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="project-0042.qgs"')
        self.assertIn("no-store", response["Cache-Control"])

    @override_settings(QGIS_ACCESS_PROJECT_FILENAME="dwb")
    def test_filename(self, now):
        self.assertEqual(self.get()["Content-Disposition"], 'attachment; filename="dwb-0042.qgs"')

    def test_server_url_and_authcfg(self, now):
        datasource = self.project().find("projectlayers/maplayer/datasource").text
        self.assertIn("url='http://testserver/oapif'", datasource)
        self.assertIn("authcfg=qgs0042 ", datasource)
        content = self.get().content.decode()
        self.assertNotIn("localhost", content)
        self.assertNotIn("qgisacc", content)

    @override_settings(QGIS_ACCESS_SERVER_URL="https://qgis.example.com/")
    def test_server_url_setting(self, now):
        datasource = self.project().find("projectlayers/maplayer/datasource").text
        self.assertIn("url='https://qgis.example.com/oapif'", datasource)

    @override_settings(QGIS_ACCESS_AUTHCFG_PREFIX="dwb")
    def test_authcfg_prefix(self, now):
        self.assertIn("authcfg=dwb0042 ", self.project().find("projectlayers/maplayer/datasource").text)

    def test_root_tag(self, now):
        self.assertEqual(
            self.project().attrib,
            {
                "projectname": "Test project",
                "version": "3.40.0-Bratislava",
                "saveUser": "alice",
                "saveUserFull": "Alice Liddell",
                "saveDateTime": "2026-09-30T12:00:00",
            },
        )

    def test_full_name_falls_back_on_the_username(self, now):
        self.user.first_name = self.user.last_name = ""
        self.user.save()
        self.assertEqual(self.project().get("saveUserFull"), "alice")

    def test_values_are_escaped(self, now):
        self.user.first_name = 'A & "B" <C>'
        self.user.last_name = "d'E"
        self.user.save()
        self.assertEqual(self.project().get("saveUserFull"), 'A & "B" <C> d\'E')

    def test_context(self, now):
        self.assertEqual(self.variables(self.project()), {"user_id": "42", "username": "alice", "team": None})

    @override_settings(QGIS_ACCESS_PROJECT_CONTEXT="tests.context.extra_context")
    def test_extra_context(self, now):
        self.assertEqual(
            self.variables(self.project()), {"user_id": "42", "username": "alice", "team": "team of alice"}
        )

    @override_settings(QGIS_ACCESS_PROJECT_CONTEXT=lambda request: {"team": "blue"})
    def test_extra_context_callable(self, now):
        self.assertEqual(self.variables(self.project())["team"], "blue")

    @override_settings(
        QGIS_ACCESS_PROJECT_TEMPLATE="minimal.qgs",
        QGIS_ACCESS_PROJECT_URL_PLACEHOLDER="https://example.test:8000",
        QGIS_ACCESS_PROJECT_AUTHCFG_PLACEHOLDER="abc1234",
    )
    def test_placeholders_and_missing_root_attributes(self, now):
        project = self.project()
        self.assertEqual(project.find("datasource").text, "authcfg=qgs0042 url='http://testserver/oapif'")
        self.assertEqual(
            project.attrib,
            {
                "projectname": "Minimal",
                "version": "3.34.0-Prizren",
                "saveUser": "alice",
                "saveUserFull": "Alice Liddell",
                "saveDateTime": "2026-09-30T12:00:00",
            },
        )

    def test_template_is_prepared_once(self, now):
        self.get()
        self.get()
        self.assertEqual(project_template.cache_info().misses, 1)
        self.assertEqual(project_template.cache_info().hits, 1)

    @override_settings(QGIS_ACCESS_PROJECT_TEMPLATE=None)
    def test_no_template(self, now):
        self.assertEqual(self.client.get(URL).status_code, 404)

    def test_permission_is_required(self, now):
        self.client.force_login(User.objects.create_user("bob"))
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_anonymous_requests_go_to_the_login_page(self, now):
        self.client.logout()
        response = self.client.get(URL)
        self.assertRedirects(response, f"/accounts/login/?next={URL}", fetch_redirect_response=False)
