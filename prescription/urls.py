from django.urls import path
from . import views
urlpatterns = [
    path("", views.prescription_list, name="prescription_list"),
    path("<int:pk>/", views.prescription_detail, name="prescription_detail"),
    path("add/<int:consultation_id>/", views.add_prescription, name="add_prescription"),
]