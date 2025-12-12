from django.db import models
from clinicmanager.models import Clinic
from django.contrib.auth import get_user_model
from patient.models import Patient, Consultation
from decimal import Decimal
from django.utils import timezone
# assuming you already have these apps


User = get_user_model()

class PaystackSubaccount(models.Model):
    clinic = models.OneToOneField(Clinic, on_delete=models.CASCADE, related_name='paystack_subaccount')
    subaccount_code = models.CharField(max_length=255, blank=True, null=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    raw_response = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Paystack subaccount for {self.clinic.name}"

# billing/models.py



class Bill(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bill #{self.id} - {self.patient}"

    @property
    def status(self):
        return "Paid" if self.is_paid else "Unpaid"


class Payment(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="payments")
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("manual", "Manual"),
        ],
        default="pending",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    paystack_response = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.reference} - {self.status}"

    def mark_as_paid(self, manual=False):
        self.status = "manual" if manual else "success"
        self.paid_at = timezone.now()
        self.bill.is_paid = True
        self.bill.save()
        self.save()


class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
