from django.contrib import admin
from django.utils.html import format_html

from .models import Consultation, Doctor, Patient, Queue

admin.site.site_header = "Medwema EMR Admin"
admin.site.site_title = "Medwema Admin"
admin.site.index_title = "Welcome to Medwema EMR"


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "specialization", "phone_number", "email", "clinic")
    search_fields = ("name", "email", "phone_number")
    list_filter = ("specialization", "clinic")
    list_select_related = ("clinic",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "patient_number",
        "name",
        "age_display",
        "gender",
        "phone_number",
        "doctor",
        "date_registered",
        "is_active",
    )
    search_fields = ("name", "phone_number", "patient_number", "email")
    list_filter = ("gender", "is_active", "blood_group", "date_registered", "doctor")
    date_hierarchy = "date_registered"
    ordering = ("-date_registered",)
    fieldsets = (
        ("Personal Info", {"fields": ("name", "date_of_birth", "gender", "blood_group", "marital_status")}),
        ("Contact", {"fields": ("phone_number", "email", "address")}),
        ("Clinic", {"fields": ("clinic", "doctor", "patient_number")}),
        ("Status", {"fields": ("is_active",)}),
    )

    @admin.display(description="Age", ordering="date_of_birth")
    def age_display(self, obj):
        return obj.age()


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = (
        "consultation_number",
        "patient_name",
        "doctor_name",
        "date",
        "status",
    )
    search_fields = ("patient__name", "diagnosis", "consultation_number")
    list_filter = ("status", "date", "doctor")
    date_hierarchy = "date"
    list_select_related = ("patient", "doctor")
    ordering = ("-date",)

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"

    @admin.display(description="Doctor", ordering="doctor__name")
    def doctor_name(self, obj):
        return obj.doctor.name if obj.doctor else "-"

    @admin.display(description="Clinic", ordering="clinic__name")
    def clinic_name(self, obj):
        return obj.clinic.name if obj.clinic else "-"


@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = (
        "queue_number",
        "patient_name",
        "doctor_name",
        "clinic_name",
        "status",
        "priority",
        "priority_badge",
        "created_at",
    )
    search_fields = ("patient__name", "queue_number")
    list_filter = ("status", "priority", "created_at", "clinic", "doctor")
    list_select_related = ("patient", "doctor", "clinic")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"

    @admin.display(description="Doctor", ordering="doctor__name")
    def doctor_name(self, obj):
        return obj.doctor.name if obj.doctor else "-"

    @admin.display(description="Clinic", ordering="clinic__name")
    def clinic_name(self, obj):
        return obj.clinic.name if obj.clinic else "-"

    @admin.display(description="Priority")
    def priority_badge(self, obj):
        colors = {"high": "#dc2626", "medium": "#d97706", "low": "#16a34a"}
        color = colors.get(obj.priority, "#64748b")
        return format_html(
            '<span style="color:{};font-weight:600;text-transform:capitalize;">● {}</span>',
            color, obj.priority,
        )
