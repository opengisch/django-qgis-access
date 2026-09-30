from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from django_qgis_access.models import ApiKey, ensure_api_key

User = get_user_model()


class ApiKeyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice")

    def test_ensure_api_key_mints_one_key(self):
        api_key = ensure_api_key(self.user)
        self.assertEqual(api_key.user, self.user)
        self.assertEqual(ensure_api_key(self.user), api_key)
        self.assertEqual(ApiKey.objects.count(), 1)

    def test_ensure_api_key_reuses_an_existing_key(self):
        api_key = ApiKey.objects.create(user=self.user)
        self.assertEqual(ensure_api_key(self.user), api_key)

    def test_keys_are_distinct(self):
        other = User.objects.create_user("bob")
        self.assertNotEqual(ensure_api_key(self.user).key, ensure_api_key(other).key)

    def test_str_shows_the_last_four_characters(self):
        api_key = ensure_api_key(self.user)
        self.assertEqual(str(api_key), f"QGIS key ···· {str(api_key.key)[-4:]}")

    def test_keys_go_with_their_user(self):
        ensure_api_key(self.user)
        self.user.delete()
        self.assertFalse(ApiKey.objects.exists())

    def test_download_permission(self):
        permission = Permission.objects.get(content_type__app_label="django_qgis_access", codename="download_qgis")
        self.assertEqual(permission.name, "Can download the QGIS project and auth file")
        self.user.user_permissions.add(permission)
        self.assertTrue(User.objects.get(pk=self.user.pk).has_perm("django_qgis_access.download_qgis"))
