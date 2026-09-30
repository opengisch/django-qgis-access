from django.urls import path

from . import views
from .admin import site
from .api import api

urlpatterns = [
    path("admin/", site.urls),
    path("api/", api.urls),
    path("oapif/whoami", views.whoami),
    path("oapif/async-whoami", views.async_whoami),
    path("other/whoami", views.whoami),
]
