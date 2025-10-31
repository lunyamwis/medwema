from django.urls import path
from . import views


urlpatterns = [
    path('', views.lab_dashboard, name='dashboard'),
    path('add-result/', views.add_lab_result, name='add_result'),
    path('edit/<int:consultation_id>/', views.edit_lab_results, name='edit_lab_results'),
    path('view/<int:consultation_id>/', views.view_lab_results, name='view_lab_results'),
    path('print/<int:consultation_id>/', views.print_lab_results, name='print_lab_results'),
]
