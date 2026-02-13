from django.urls import path
from . import views


urlpatterns = [
    path('', views.lab_dashboard, name='lab_dashboard'),
    path('search/', views.lab_search_dashboard, name='lab_search_dashboard'),
    path('results/', views.lab_results_dashboard, name='lab_results_dashboard'),
    path('add-result/<int:consultation_id>/', views.add_lab_result, name='add_result'),
    path('edit/<int:consultation_id>/', views.edit_lab_results, name='edit_lab_results'),
    path('view/<int:consultation_id>/', views.view_lab_results, name='view_lab_results'),
    path('print/<int:consultation_id>/', views.print_lab_results, name='print_lab_results'),
    path("lab/<int:lab_id>/queue/", views.lab_queue_view, name="lab_queue"),
    path("lab/queue/<int:queue_id>/start/", views.start_lab_test, name="start_lab_test"),
    path("lab/queue/<int:queue_id>/complete/", views.complete_lab_test, name="complete_lab_test"),
    path('send-to-lab/<int:consultation_id>/<int:patient_id>/', views.send_to_lab, name='send_to_lab'),
    path('ajax/consultation-search/', views.ajax_consultation_search, name='ajax_consultation_search'),
    path('ajax/labtest-search/', views.ajax_labtest_search, name='ajax_labtest_search'),
    path('api/lab-queue-count/', views.lab_queue_count_api, name='lab_queue_count_api'),
    path("consultations/search/", views.consultation_search, name="consultation_search"),

]
