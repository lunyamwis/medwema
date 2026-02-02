from django.urls import path
from . import views

app_name = "specialists"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Specialist tasks
    path("tasks/", views.task_list, name="task_list"),
    path("tasks/new/", views.task_create, name="task_create"),
    path("tasks/<int:task_id>/bill/", views.task_bill_service, name="task_bill_service"),

    # Alerts
    path("queue/<int:queue_id>/arrived/", views.patient_arrived_alert, name="patient_arrived_alert"),

    # Sonography
    path("sonography/", views.sonography_list, name="sonography_list"),
    path("sonography/new/", views.sonography_create, name="sonography_create"),
    path("sonography/<int:pk>/", views.sonography_detail, name="sonography_detail"),

    # Nursing
    path("nursing/", views.nursing_list, name="nursing_list"),
    path("nursing/new/", views.nursing_create, name="nursing_create"),
    path("nursing/<int:pk>/", views.nursing_detail, name="nursing_detail"),

    # External lab
    path("external-lab/", views.external_lab_list, name="external_lab_list"),
    path("external-lab/new/", views.external_lab_create, name="external_lab_create"),
    path("external-lab/<int:pk>/", views.external_lab_detail, name="external_lab_detail"),
    path("external-lab/<int:pk>/send/", views.external_lab_send, name="external_lab_send"),
    path("external-lab/<int:pk>/upload/", views.external_lab_upload_result, name="external_lab_upload_result"),

    # Home visit
    path("home-visits/", views.home_visit_list, name="home_visit_list"),
    path("home-visits/new/", views.home_visit_create, name="home_visit_create"),

    # Supplies
    path("supplies/", views.supply_invoice_list, name="supply_invoice_list"),
    path("supplies/new/", views.supply_invoice_create, name="supply_invoice_create"),

    # Debts
    path("debts/", views.debts_list, name="debts_list"),
    path("debts/<int:pk>/", views.debt_detail, name="debt_detail"),
    path("debts/<int:pk>/followup/", views.debt_add_followup, name="debt_add_followup"),

    # Equipment
    path("equipment/", views.equipment_list, name="equipment_list"),
    path("equipment/new/", views.equipment_create, name="equipment_create"),
]
