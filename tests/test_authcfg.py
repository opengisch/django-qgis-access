import re
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.db import models
from django.test import SimpleTestCase, override_settings

from django_qgis_access.authcfg import MAX_USER_ID, authcfg_id, encode_user_id
from django_qgis_access.checks import check_settings

# what QGIS takes for the id of an authentication configuration
QGIS_AUTHCFG = re.compile(r"[A-Za-z0-9]{7}")


def user(pk):
    return SimpleNamespace(pk=pk)


class AuthcfgIdTests(SimpleTestCase):
    def test_small_ids_are_decimal(self):
        self.assertEqual(authcfg_id(user(0)), "qgs0000")
        self.assertEqual(authcfg_id(user(42)), "qgs0042")
        self.assertEqual(authcfg_id(user(9999)), "qgs9999")

    @override_settings(QGIS_ACCESS_AUTHCFG_PREFIX="dwb")
    def test_prefix(self):
        self.assertEqual(authcfg_id(user(42)), "dwb0042")

    def test_large_ids_start_with_a_letter(self):
        self.assertEqual(authcfg_id(user(10000)), "qgsa000")
        self.assertEqual(authcfg_id(user(10035)), "qgsa00z")
        self.assertEqual(authcfg_id(user(10036)), "qgsa010")
        self.assertEqual(authcfg_id(user(10000 + 36**3)), "qgsb000")
        self.assertEqual(authcfg_id(user(MAX_USER_ID)), "qgszzzz")
        self.assertEqual(MAX_USER_ID, 1_223_055)

    def test_ids_are_what_qgis_takes(self):
        for pk in (0, 1, 9999, 10000, 123_456, MAX_USER_ID):
            self.assertRegex(authcfg_id(user(pk)), QGIS_AUTHCFG)

    def test_ids_are_distinct(self):
        pks = [*range(60_000), *range(MAX_USER_ID - 60_000, MAX_USER_ID + 1)]
        self.assertEqual(len({encode_user_id(pk) for pk in pks}), len(pks))

    def test_ids_out_of_range(self):
        for pk in (-1, MAX_USER_ID + 1):
            with self.assertRaises(ValueError):
                authcfg_id(user(pk))


class CheckTests(SimpleTestCase):
    def check_ids(self):
        return [error.id for error in check_settings(None)]

    def test_default_settings_pass(self):
        self.assertEqual(self.check_ids(), [])
        call_command("check")

    def test_prefix_must_be_three_alphanumeric_characters(self):
        for prefix in ("dwb", "ABC", "a1B"):
            with self.subTest(prefix=prefix), override_settings(QGIS_ACCESS_AUTHCFG_PREFIX=prefix):
                self.assertEqual(self.check_ids(), [])
        for prefix in ("ab", "abcd", "a-b", "äbc", "a b", "", None, 123):
            with self.subTest(prefix=prefix), override_settings(QGIS_ACCESS_AUTHCFG_PREFIX=prefix):
                self.assertEqual(self.check_ids(), ["django_qgis_access.E001"])

    @override_settings(QGIS_ACCESS_AUTHCFG_PREFIX="ab")
    def test_check_is_registered(self):
        with self.assertRaisesMessage(SystemCheckError, "django_qgis_access.E001"):
            call_command("check")

    def test_user_pk_must_be_an_integer(self):
        uuid_user = SimpleNamespace(_meta=SimpleNamespace(pk=models.UUIDField(primary_key=True)))
        with mock.patch("django_qgis_access.checks.get_user_model", return_value=uuid_user):
            self.assertEqual(self.check_ids(), ["django_qgis_access.E002"])
