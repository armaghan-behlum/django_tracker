from django.urls import path

from . import views

urlpatterns = [
    path(
        "",
        views.incident_report_create,
        name="incident_report_create",
    ),

    path(
        "report/<uuid:uuid>/submitted/",
        views.incident_report_success,
        name="incident_report_success",
    ),

    path(
        "report/<uuid:uuid>/ucp/",
        views.ucp_offer,
        name="ucp_offer",
    ),
]