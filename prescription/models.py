from django.contrib.auth import get_user_model
from django.db import models

from inventory.models import Item
from patient.models import Consultation

User = get_user_model()


class Prescription(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="prescriptions")
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True, related_name="prescriptions")
    quantity = models.PositiveIntegerField(default=1)
    dosage = models.CharField(max_length=200, blank=True, null=True)
    frequency = models.CharField(max_length=100, blank=True, null=True)
    duration = models.CharField(max_length=100, blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    dispensed = models.BooleanField(default=False, db_index=True)
    prescribed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="prescribed_prescriptions")
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="dispensed_prescriptions")
    prescribed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    
    class Meta:
        ordering = ["-prescribed_at"]
        indexes = [
            models.Index(fields=["consultation"]),
            models.Index(fields=["dispensed"]),
            models.Index(fields=["item"]),
        ]

    def __str__(self) -> str:
        return f"{self.item.name} × {self.quantity} — {self.consultation}"
