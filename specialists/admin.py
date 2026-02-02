from django.contrib import admin
from .models import *

admin.site.register(SpecialistProfile)
admin.site.register(ServiceCatalog)
admin.site.register(NotificationForSpecialist)
admin.site.register(SpecialistTask)
admin.site.register(SonographyStudy)
admin.site.register(NursingNote)
admin.site.register(ExternalLabRequest)
admin.site.register(ExternalLabResult)
admin.site.register(HomeVisit)
admin.site.register(SupplyInvoice)
admin.site.register(SupplyInvoiceItem)
admin.site.register(DebtCase)
admin.site.register(DebtFollowUp)
admin.site.register(EquipmentItem)
