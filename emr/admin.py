from django.contrib import admin
from .models import LabResult, LabTest, Lab
# Register your models here.

admin.site.register(LabTest)
admin.site.register(LabResult)
admin.site.register(Lab)
