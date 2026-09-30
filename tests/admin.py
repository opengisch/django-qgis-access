"""An admin site of its own, with the API key inline on the users."""

from django.contrib import admin
from django.contrib.auth import get_user_model

from django_qgis_access.admin import ApiKeyInline


class UserAdmin(admin.ModelAdmin):
    fields = ["username"]
    inlines = [ApiKeyInline]


site = admin.AdminSite(name="test_admin")
site.register(get_user_model(), UserAdmin)
