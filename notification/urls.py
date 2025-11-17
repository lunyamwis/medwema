from django.urls import path
from . import views

urlpatterns = [
    path("generate-vapid/", views.get_or_generate_vapid_keys, name="generate_vapid"),
    path('save-subscription/',views.save_info,name='save-notification-subscription'),
]
