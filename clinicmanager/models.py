from django.db import models
from authentication.models import User

class Clinic(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    created_by = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="clinic"
    )
    staff = models.ManyToManyField(
        User, related_name="clinics", blank=True, help_text="Clinic staff members"
    )
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
