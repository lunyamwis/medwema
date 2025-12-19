from django.db import models
from patient.models import Consultation
from inventory.models import Item

class Prescription(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    prescribed_at = models.DateTimeField(auto_now_add=True)
    instructions = models.TextField(blank=True, null=True)
    dispensed = models.BooleanField(default=False)


    