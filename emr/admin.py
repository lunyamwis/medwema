from django.contrib import admin
from .models import LabResult, LabTest, Lab, LabQueue
# Register your models here.

admin.site.register(LabTest)
admin.site.register(LabResult)
admin.site.register(Lab)
admin.site.register(LabQueue)