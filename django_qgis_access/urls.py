from django.urls import path

from . import views

app_name = "qgis_access"

urlpatterns = [
    path("auth.xml", views.auth_xml, name="auth_xml"),
    path("project.qgs", views.project, name="project"),
]
