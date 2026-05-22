from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("owner", "Clinic Owner"),
        ("doctor", "Doctor"),
        ("receptionist", "Receptionist"),
        ("nurse", "Nurse"),
        ("lab", "Lab Technician"),
        ("admin", "Administrator"),
    ]

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="receptionist", db_index=True)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/", null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    vapid_public_key = models.CharField(max_length=500, null=True, blank=True)
    vapid_private_key = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "role"]),
        ]

    def is_doctor(self) -> bool:
        return self.role == "doctor"

    def is_receptionist(self) -> bool:
        return self.role == "receptionist"

    def is_lab_tech(self) -> bool:
        return self.role == "lab"

    def is_nurse(self) -> bool:
        return self.role == "nurse"

    def is_owner(self) -> bool:
        return self.role == "owner"

    def get_full_name(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username

    def __str__(self) -> str:
        return self.get_full_name()
