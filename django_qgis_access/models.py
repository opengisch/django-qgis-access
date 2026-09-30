import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ApiKey(models.Model):
    """A permanent credential of a QGIS user, whose token is `key`.

    The token is not the primary key: forms and URLs carry the primary key of a row, the admin to delete it
    for one, and would hand the token to whoever may see them.
    """

    id = models.BigAutoField(primary_key=True)
    key = models.UUIDField(_("key"), unique=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
        verbose_name=_("user"),
    )

    class Meta:
        verbose_name = _("API key")
        verbose_name_plural = _("API keys")
        permissions = [
            ("download_qgis", "Can download the QGIS project and auth file"),
        ]

    def __str__(self):
        return f"QGIS key ···· {str(self.key)[-4:]}"


def ensure_api_key(user) -> ApiKey:
    """The key of `user`, minted on the first call.

    Keys are issued, never entered: they come to be when their owner downloads the auth file.
    """
    api_key = user.api_keys.first()
    if api_key is None:
        api_key = ApiKey.objects.create(user=user)
    return api_key
