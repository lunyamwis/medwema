from django.urls import path

from patient import views

urlpatterns = [
    # Dashboard / patient list
    path("", views.patient_list_view, name="patient_list"),

    # Doctors
    path("doctors/", views.doctor_list_view, name="doctor_list"),
    path("doctors/<int:pk>/", views.doctor_detail, name="doctor_detail"),

    # Patient CRUD
    path("register/", views.register_patient, name="register_patient"),
    path("<int:pk>/", views.patient_detail, name="patient_detail"),
    path("<int:pk>/edit/", views.patient_edit, name="patient_edit"),
    path("<int:patient_id>/consultations/", views.patient_consultations, name="patient_consultations"),

    # Consultations
    path("consultations/", views.consultation_list_view, name="consultation_list"),
    path("<int:patient_id>/consultations/new/", views.new_consultation, name="new_consultation"),
    path("<int:patient_id>/consultations/<int:consultation_id>/edit/", views.edit_consultation, name="edit_consultation"),
    path("consultations/<int:consultation_id>/", views.consultation_detail, name="consultation_detail"),
    path("consultations/<int:consultation_id>/pdf/", views.consultation_pdf, name="consultation_pdf"),

    # Queue management
    path("add-to-queue/<int:doctor_id>/<int:patient_id>/", views.add_to_queue, name="add_to_queue"),
    path("add-to-queue-select/<int:patient_id>/", views.add_to_queue_select, name="add_to_queue_select"),
    path("queue/<int:queue_id>/start/", views.start_consultation, name="start_consultation"),
    path("queue/<int:queue_id>/complete/", views.complete_consultation, name="complete_consultation"),

    # AJAX / API
    path("add-lab-test/", views.add_lab_test, name="add_lab_test"),
    path("api/patient-queue-count/", views.patient_queue_count_api, name="patient_queue_count_api"),
    path("api/patient-complete-count/", views.patient_complete_count_api, name="patient_complete_count_api"),
    path("speech-to-consultation/<int:patient_id>/", views.speech_to_consultation, name="speech_to_consultation"),
    path("pipeline-notification/", views.pipeline_notification, name="pipeline_notification"),
]
