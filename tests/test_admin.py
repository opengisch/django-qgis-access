from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from django_qgis_access.admin import ApiKeyInline
from django_qgis_access.models import ApiKey, ensure_api_key

from .admin import site

User = get_user_model()


class FormInputs(HTMLParser):
    """The name and value of the inputs of a page, as a browser would post them."""

    def __init__(self, html):
        super().__init__()
        self.data = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") in ("hidden", "text") and attrs.get("name"):
            self.data[attrs["name"]] = attrs.get("value") or ""


class ApiKeyInlineTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin")
        self.user = User.objects.create_user("alice")
        self.api_key = ensure_api_key(self.user)
        self.url = reverse("test_admin:auth_user_change", args=[self.user.pk])
        self.client.force_login(self.admin)

    def test_shows_the_last_four_characters(self):
        response = self.client.get(self.url)
        self.assertContains(response, f"<p>···· {str(self.api_key.key)[-4:]}</p>", html=True)
        self.assertContains(response, f'<input type="hidden" name="api_keys-0-id" value="{self.api_key.pk}"')

    def test_never_shows_a_whole_key(self):
        self.assertNotContains(self.client.get(self.url), str(self.api_key.key))

    def test_keys_cannot_be_added(self):
        response = self.client.get(self.url)
        self.assertEqual(FormInputs(response.content.decode()).data["api_keys-MAX_NUM_FORMS"], "0")
        inline = ApiKeyInline(User, site)
        self.assertFalse(inline.has_add_permission(response.wsgi_request, self.user))
        self.assertEqual(inline.extra, 0)

    def test_deleting_revokes(self):
        other_key = ensure_api_key(User.objects.create_user("bob"))
        data = FormInputs(self.client.get(self.url).content.decode()).data
        self.assertEqual(data["api_keys-0-id"], str(self.api_key.pk))

        response = self.client.post(self.url, {**data, "api_keys-0-DELETE": "on"})

        self.assertRedirects(response, reverse("test_admin:auth_user_changelist"))
        self.assertEqual(list(ApiKey.objects.all()), [other_key])


class SuperuserApiKeyTests(TestCase):
    """A key acts as its owner: a staff user who may manage keys must not get hold of those of superusers."""

    def setUp(self):
        self.root = User.objects.create_superuser("root")
        self.root_key = ensure_api_key(self.root)
        self.url = reverse("test_admin:auth_user_change", args=[self.root.pk])
        self.staff = User.objects.create_user("staff", is_staff=True)
        self.staff.user_permissions.set(
            Permission.objects.filter(codename__in=["view_user", "change_user", "view_apikey", "delete_apikey"])
        )

    def test_hidden_from_other_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, str(self.root_key.key)[-4:])
        self.assertNotIn("api_keys-0-id", FormInputs(response.content.decode()).data)

    def test_other_keys_stay_manageable_by_staff(self):
        api_key = ensure_api_key(User.objects.create_user("alice"))
        self.client.force_login(self.staff)
        response = self.client.get(reverse("test_admin:auth_user_change", args=[api_key.user.pk]))
        self.assertContains(response, f"<p>···· {str(api_key.key)[-4:]}</p>", html=True)
        self.assertNotContains(response, str(api_key.key))

    def test_listed_to_superusers(self):
        self.client.force_login(User.objects.create_superuser("admin"))
        response = self.client.get(self.url)
        self.assertContains(response, f"<p>···· {str(self.root_key.key)[-4:]}</p>", html=True)
        self.assertNotContains(response, str(self.root_key.key))
