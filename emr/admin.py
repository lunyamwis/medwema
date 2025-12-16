from django.contrib import admin
from .models import LabResult, LabTest, Lab, LabQueue
# Register your models here.



@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "unit", "price", )
    list_filter = ("created_at")
    search_fields = ("name",)
admin.site.register(LabResult)
admin.site.register(Lab)
admin.site.register(LabQueue)