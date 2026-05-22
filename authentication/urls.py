from django.urls import path

from authentication import views

urlpatterns = [
    path("", views.profile_view, name="user_profile"),
]
