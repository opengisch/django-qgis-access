from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

User = get_user_model()

TEMPLATE = "django_qgis_access/admin_downloads.html"


class AdminDownloadsTests(TestCase):
    def render(self, user, **context):
        request = RequestFactory().get("/admin/")
        request.user = user
        return render_to_string(TEMPLATE, context, request=request)

    def qgis_user(self):
        user = User.objects.create_user("alice")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="django_qgis_access", codename="download_qgis")
        )
        return User.objects.get(pk=user.pk)

    def test_links(self):
        html = self.render(self.qgis_user())
        self.assertInHTML('<a href="/qgis/project.qgs">Download QGIS project</a>', html)
        self.assertInHTML('<a href="/qgis/auth.xml">Download authentication file</a>', html)

    def test_hidden_without_the_permission(self):
        self.assertEqual(self.render(User.objects.create_user("bob")).strip(), "")

    def test_without_the_project(self):
        html = self.render(self.qgis_user(), hide_project=True)
        self.assertNotIn("/qgis/project.qgs", html)
        self.assertInHTML('<a href="/qgis/auth.xml">Download authentication file</a>', html)
