from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Roles for clinic staff
    ROLE_CHOICES = [
        ("owner", "Clinic Owner"),
        ("doctor", "Doctor"),
        ("receptionist", "Receptionist"),
        ("nurse", "Nurse"),
        ("lab", "Lab Technician"),
        ("admin", "Administrator"),
    ]

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="receptionist")
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    vapid_public_key = models.CharField(max_length=500, null=True, blank=True)
    vapid_private_key = models.CharField(max_length=255, null=True, blank=True)
    # any other global profile fields here

    def is_doctor(self):
        return self.role == "doctor"

    def is_receptionist(self):
        return self.role == "receptionist"
