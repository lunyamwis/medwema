from django.contrib import admin

from .models import (
    DebtCase,
    DebtFollowUp,
    EquipmentItem,
    ExternalLabRequest,
    ExternalLabResult,
    HomeVisit,
    NotificationForSpecialist,
    ServiceCatalog,
    SpecialistProfile,
    SpecialistTask,
    SonographyStudy,
    NursingNote,
    SupplyInvoice,
    SupplyInvoiceItem,
)


@admin.register(SpecialistTask)
class SpecialistTaskAdmin(admin.ModelAdmin):
    list_display = (
        "patient_name",
        "role",
        "service",
        "status",
        "assigned_to",
        "created_at",
    )
    search_fields = ("patient__name",)
    list_filter = ("status", "role", "clinic")
    list_select_related = ("patient", "assigned_to", "service")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"


@admin.register(SonographyStudy)
class SonographyStudyAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "study_type", "performed_by", "performed_at")
    search_fields = ("patient__name",)
    list_filter = ("study_type", "performed_at")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"


@admin.register(NursingNote)
class NursingNoteAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "category", "created_by", "created_at")
    search_fields = ("patient__name",)
    list_filter = ("category", "created_at")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"


@admin.register(DebtCase)
class DebtCaseAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "balance", "status", "next_followup_at")
    search_fields = ("patient__name",)
    list_filter = ("status",)

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"


@admin.register(EquipmentItem)
class EquipmentItemAdmin(admin.ModelAdmin):
    list_display = ("name", "qty_available", "reorder_level", "is_low_stock_flag")
    search_fields = ("name",)
    list_filter = ("clinic",)

    @admin.display(description="Low Stock?", boolean=True)
    def is_low_stock_flag(self, obj):
        return obj.is_low_stock()


@admin.register(ServiceCatalog)
class ServiceCatalogAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "price", "is_active", "clinic")
    search_fields = ("name",)
    list_filter = ("role", "is_active", "clinic")
    list_editable = ("is_active",)


@admin.register(HomeVisit)
class HomeVisitAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "visit_date", "status", "clinician", "clinic")
    search_fields = ("patient__name",)
    list_filter = ("status", "visit_date")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"


@admin.register(SupplyInvoice)
class SupplyInvoiceAdmin(admin.ModelAdmin):
    list_display = ("vendor", "invoice_number", "invoice_date", "total_amount", "clinic")
    search_fields = ("vendor", "invoice_number")
    list_filter = ("invoice_date", "clinic")


@admin.register(ExternalLabRequest)
class ExternalLabRequestAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "lab_name", "status", "created_at")
    search_fields = ("patient__name", "lab_name")
    list_filter = ("status", "created_at")

    @admin.display(description="Patient", ordering="patient__name")
    def patient_name(self, obj):
        return obj.patient.name if obj.patient else "-"


@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "clinic", "is_active")
    search_fields = ("user__username", "user__email")
    list_filter = ("role", "is_active", "clinic")


@admin.register(NotificationForSpecialist)
class NotificationForSpecialistAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "seen", "created_at", "clinic")
    search_fields = ("title", "recipient__username")
    list_filter = ("seen", "clinic", "created_at")


@admin.register(ExternalLabResult)
class ExternalLabResultAdmin(admin.ModelAdmin):
    list_display = ("request", "uploaded_by", "uploaded_at")
    search_fields = ("request__patient__name",)
    list_filter = ("uploaded_at",)


@admin.register(SupplyInvoiceItem)
class SupplyInvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("description", "qty", "unit_cost", "line_total", "invoice")
    search_fields = ("description",)


@admin.register(DebtFollowUp)
class DebtFollowUpAdmin(admin.ModelAdmin):
    list_display = ("debt_case", "channel", "created_by", "created_at")
    search_fields = ("debt_case__patient__name",)
    list_filter = ("channel", "created_at")
