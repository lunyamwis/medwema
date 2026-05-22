from django.contrib import admin

from .models import Lab, LabQueue, LabResult, LabTest


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ("name", "lab_type", "clinic")
    search_fields = ("name",)
    list_filter = ("lab_type",)


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "unit", "price", "is_active")
    search_fields = ("name",)
    list_filter = ("category", "is_active")
    list_editable = ("is_active",)


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = (
        "patient_name",
        "lab_test",
        "result_value",
        "result_name",
        "result_date",
    )
    search_fields = ("consultation__patient__name", "lab_test__name")
    list_filter = ("result_date", "lab_test")
    list_select_related = ("consultation__patient", "lab_test")

    @admin.display(description="Patient", ordering="consultation__patient__name")
    def patient_name(self, obj):
        if obj.consultation and obj.consultation.patient:
            return obj.consultation.patient.name
        return "-"


@admin.register(LabQueue)
class LabQueueAdmin(admin.ModelAdmin):
    list_display = (
        "queue_number",
        "patient_name",
        "lab_test",
        "status",
        "created_at",
    )
    search_fields = ("patient__name",)
    list_filter = ("status", "created_at")
    list_select_related = ("patient", "lab_test", "clinic")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"
