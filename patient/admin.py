from django.contrib import admin
from .models import Doctor, Patient, Consultation
# Register your models here.
admin.site.site_header = "Medwema Admin"
admin.site.site_title = "Medwema Admin Portal"
admin.site.index_title = "Welcome to Medwema Admin Portal"

admin.site.register(Doctor)
admin.site.register(Patient)
admin.site.register(Consultation)

