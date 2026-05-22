from django.contrib import admin

from .models import Bill, BillItem, Payment, PaystackSubaccount


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 0
    readonly_fields = ("total",)


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient_name",
        "total_amount",
        "discount",
        "net_amount_display",
        "is_paid",
        "clinic_name",
        "created_at",
    )
    search_fields = ("patient__name",)
    list_filter = ("is_paid", "created_at", "clinic")
    inlines = (BillItemInline,)
    list_select_related = ("patient", "clinic")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"

    @admin.display(description="Clinic", ordering="clinic__name")
    def clinic_name(self, obj):
        return obj.clinic.name if obj.clinic else "-"

    @admin.display(description="Net Amount")
    def net_amount_display(self, obj):
        return obj.net_amount


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "reference",
        "patient_name",
        "amount",
        "payment_method",
        "status",
        "paid_at",
    )
    search_fields = ("reference", "receipt_number", "bill__patient__name")
    list_filter = ("status", "payment_method", "paid_at")
    list_select_related = ("bill__patient",)

    @admin.display(description="Patient", ordering="bill__patient__name")
    def patient_name(self, obj):
        if obj.bill and obj.bill.patient:
            return obj.bill.patient.name
        return "-"


@admin.register(PaystackSubaccount)
class PaystackSubaccountAdmin(admin.ModelAdmin):
    list_display = ("clinic", "subaccount_code", "business_name", "created_at")
    search_fields = ("clinic__name", "subaccount_code", "business_name")
