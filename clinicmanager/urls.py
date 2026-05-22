from django.urls import path

from clinicmanager import views

urlpatterns = [
    path("", views.clinic_settings, name="clinic_settings"),
]
