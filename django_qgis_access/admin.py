from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import ApiKey


class ApiKeyInlineMixin:
    """The API keys of a user, as an inline of the user admin.

    Combine it with the inline class of the admin in use, as `ApiKeyInline` does with the stock one;
    with Unfold: `class ApiKeyInline(ApiKeyInlineMixin, unfold.admin.TabularInline)`.

    Keys are minted by the download of the auth file, so none can be added here. Deleting one revokes
    it: its owner gets a new one with the next download. Only the last four characters of a key are
    shown, and the form carries the primary key of the rows, never their keys. A key acts as its
    owner, so the keys of superusers are only listed to superusers.
    """

    model = ApiKey
    extra = 0
    fields = ["masked_key"]
    readonly_fields = ["masked_key"]

    @admin.display(description=_("key"))
    def masked_key(self, obj):
        return f"···· {str(obj.key)[-4:]}"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.exclude(user__is_superuser=True)

    def has_add_permission(self, request, obj=None):
        return False


class ApiKeyInline(ApiKeyInlineMixin, admin.TabularInline):
    pass
