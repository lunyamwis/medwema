# billing/admin.py
from django.contrib import admin
from .models import Bill, Payment

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "total_amount", "is_paid", "created_at")
    list_filter = ("is_paid", "created_at")
    search_fields = ("patient__name",)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "bill", "amount", "status", "paid_at")
    list_filter = ("status",)
    search_fields = ("reference",)
