from django.contrib import admin
from django.utils.html import format_html

from .models import Lab, LabQueue, LabResult, LabTest


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ("name", "lab_type", "clinic")
    search_fields = ("name",)
    list_filter = ("lab_type", "clinic")
    list_select_related = ("clinic",)


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "unit", "price", "is_active")
    search_fields = ("name", "category")
    list_filter = ("category", "is_active")
    list_editable = ("is_active",)
    ordering = ("category", "name")


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = (
        "patient_name",
        "lab_test",
        "result_value",
        "result_name",
        "result_date",
        "clinic_name",
    )
    search_fields = ("consultation__patient__name", "lab_test__name")
    list_filter = ("result_date", "lab_test", "consultation")
    date_hierarchy = "result_date"
    list_select_related = ("consultation__patient", "consultation__clinic", "lab_test")
    ordering = ("-result_date",)

    @admin.display(description="Patient", ordering="consultation__patient__name")
    def patient_name(self, obj):
        if obj.consultation and obj.consultation.patient:
            return obj.consultation.patient.name
        return "-"

    @admin.display(description="Clinic", ordering="consultation__clinic__name")
    def clinic_name(self, obj):
        if obj.consultation and obj.consultation.clinic:
            return obj.consultation.clinic.name
        return "-"


@admin.register(LabQueue)
class LabQueueAdmin(admin.ModelAdmin):
    list_display = (
        "queue_number",
        "patient_name",
        "lab_test",
        "status",
        "status_badge",
        "clinic",
        "created_at",
    )
    search_fields = ("patient__name", "queue_number")
    list_filter = ("status", "created_at", "clinic", "lab_test")
    date_hierarchy = "created_at"
    list_select_related = ("patient", "lab_test", "clinic")
    ordering = ("-created_at",)

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {"pending": "#d97706", "in_progress": "#2563eb", "completed": "#16a34a", "cancelled": "#ef4444"}
        color = colors.get(obj.status, "#64748b")
        return format_html(
            '<span style="color:{};font-weight:600;text-transform:capitalize;">● {}</span>',
            color, obj.status.replace("_", " "),
        )
