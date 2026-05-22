from django.contrib import admin

from .models import Clinic, ClinicBankDetails


class ClinicBankDetailsInline(admin.TabularInline):
    model = ClinicBankDetails
    extra = 0
    readonly_fields = ("date_created",)


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "email",
        "website",
        "is_active",
        "date_created",
    )
    search_fields = ("name", "email", "phone_number")
    list_filter = ("is_active", "date_created")
    readonly_fields = ("date_created",)
    inlines = (ClinicBankDetailsInline,)


@admin.register(ClinicBankDetails)
class ClinicBankDetailsAdmin(admin.ModelAdmin):
    list_display = ("clinic", "get_bank_name_display", "account_name", "account_type", "currency", "date_created")
    search_fields = ("clinic__name", "account_name", "account_number")
    list_filter = ("account_type", "currency", "clinic")
    list_select_related = ("clinic",)
