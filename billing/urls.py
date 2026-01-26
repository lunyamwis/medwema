from django.urls import path
from . import views


urlpatterns = [

    path("", views.billing_dashboard, name="billing_dashboard"),
    path("list/", views.billing_list, name="billing_list"),
    path("<int:pk>/", views.bill_detail, name="bill_detail"),
    path("edit/<int:pk>/", views.bill_edit, name="bill_edit"),
    path("<int:pk>/mark-paid/", views.mark_bill_paid, name="mark_bill_paid"),
    path("<int:pk>/print/", views.print_receipt, name="print_receipt"),
    path("revenue/", views.revenue_report, name="revenue_report"),
    path("initiate/<int:bill_id>/", views.initiate_payment, name="initiate_payment"),
    path("paystack/callback/", views.paystack_webhook, name="paystack_webhook"),
    path("transactions/", views.transactions_view, name="transactions_view"),

]
