from django.contrib import admin

from .models import Prescription


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = (
        "item_name",
        "patient_name",
        "quantity",
        "dosage",
        "frequency",
        "dispensed",
        "prescribed_by",
        "prescribed_at",
    )
    list_filter = ("dispensed", "prescribed_at", "item__clinic")
    search_fields = ("item__name", "consultation__patient__name", "prescribed_by__username")
    date_hierarchy = "prescribed_at"
    list_select_related = ("item", "consultation__patient", "prescribed_by")
    list_editable = ("dispensed",)
    ordering = ("-prescribed_at",)
    readonly_fields = ("prescribed_at",)
    fieldsets = (
        (None, {"fields": ("consultation", "item", "quantity", "dosage", "frequency", "duration")}),
        ("Instructions", {"fields": ("instructions",)}),
        ("Status", {"fields": ("dispensed", "dispensed_by", "prescribed_by", "prescribed_at")}),
    )

    @admin.display(description="Item", ordering="item__name")
    def item_name(self, obj):
        return obj.item.name if obj.item else "-"

    @admin.display(description="Patient", ordering="consultation__patient__name")
    def patient_name(self, obj):
        if obj.consultation and obj.consultation.patient:
            return obj.consultation.patient.name
        return "-"
