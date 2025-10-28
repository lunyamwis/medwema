# clinic/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/<int:pk>/', views.doctor_detail, name='doctor_detail'),
    path('', views.patient_list, name='patient_list'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path("patients/register/", views.register_patient, name="register_patient"),
    path("patients/success/", views.patient_success, name="patient_success"),
    path('patients/<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('patients/<int:patient_id>/consultations/new/', views.new_consultation, name='new_consultation'),
    path('patients/<int:patient_id>/consultations/', views.patient_consultations, name='patient_consultations'),
    path('consultations/<int:consultation_id>/', views.consultation_detail, name='consultation_detail'),
    path('consultations/<int:consultation_id>/pdf/', views.consultation_pdf, name='consultation_pdf'),
    path('add-to-queue/<int:doctor_id>/<int:patient_id>/', views.add_to_queue, name='add_to_queue'),
    path('add-to-queue-select/<int:patient_id>/', views.add_to_queue_select, name='add_to_queue_select'),
    path('queue/<int:queue_id>/start/', views.start_consultation, name='start_consultation'),
    path('queue/<int:queue_id>/complete/', views.complete_consultation, name='complete_consultation'),
]
