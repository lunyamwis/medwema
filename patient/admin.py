from django.contrib import admin

from .models import Consultation, Doctor, Patient, Queue

admin.site.site_header = "Medwema EMR Admin"
admin.site.site_title = "Medwema Admin"
admin.site.index_title = "Welcome to Medwema EMR"


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "specialization", "phone_number", "email")
    search_fields = ("name", "email")
    list_filter = ("specialization",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "patient_number",
        "name",
        "age",
        "gender",
        "phone_number",
        "doctor",
        "date_registered",
        "is_active",
    )
    search_fields = ("name", "phone_number", "patient_number", "email")
    list_filter = ("gender", "is_active", "blood_group", "date_registered")
    date_hierarchy = "date_registered"
    list_select_related = ("doctor", "clinic")

    @admin.display(description="Age")
    def age(self, obj):
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
    list_filter = ("status", "date")
    date_hierarchy = "date"
    list_select_related = ("patient", "doctor")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"

    @admin.display(description="Doctor", ordering="doctor__name")
    def doctor_name(self, obj):
        return obj.doctor.name if obj.doctor else "-"


@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = (
        "queue_number",
        "patient_name",
        "doctor_name",
        "status",
        "priority",
        "created_at",
    )
    search_fields = ("patient__name",)
    list_filter = ("status", "priority", "created_at")
    list_select_related = ("patient", "doctor", "clinic")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"

    @admin.display(description="Doctor", ordering="doctor__name")
    def doctor_name(self, obj):
        return obj.doctor.name if obj.doctor else "-"
