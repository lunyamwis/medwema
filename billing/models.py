from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from clinicmanager.models import Clinic
from patient.models import Consultation, Patient

User = get_user_model()


class PaystackSubaccount(models.Model):
    clinic = models.OneToOneField(Clinic, on_delete=models.CASCADE, related_name="paystack_subaccount")
    subaccount_code = models.CharField(max_length=255, blank=True, null=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    raw_response = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Paystack subaccount — {self.clinic.name}"


class Bill(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="bills")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="bills")
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="bills")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), blank=True, null=True)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), blank=True, null=True)
    is_paid = models.BooleanField(default=False, db_index=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clinic", "is_paid"]),
            models.Index(fields=["patient", "is_paid"]),
            models.Index(fields=["created_at"]),
        ]

    @property
    def status(self) -> str:
        return "Paid" if self.is_paid else "Unpaid"

    @property
    def net_amount(self) -> Decimal:
        total = self.total_amount or Decimal("0.00")
        discount = self.discount or Decimal("0.00")
        return max(Decimal("0.00"), total - discount)

    def __str__(self) -> str:
        return f"Bill #{self.id} — {self.patient}"


class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["bill"]),
        ]

    def save(self, *args, **kwargs):
        self.total = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.description} × {self.quantity}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("manual", "Manual"),
    ]
    PAYMENT_METHODS = [
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("MPESA", "M-Pesa"),
        ("ONLINE", "Online"),
        ("OTHER", "Other"),
    ]

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="payments")
    reference = models.CharField(max_length=100, db_index=True)
    receipt_number = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="CASH")
    paid_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments_created")
    paystack_response = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-paid_at", "-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["bill", "status"]),
            models.Index(fields=["paid_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            today = timezone.now().strftime("%Y%m%d")
            count = Payment.objects.filter(paid_at__date=timezone.now().date()).count() + 1
            self.receipt_number = f"RCP{today}{count:04d}"
        super().save(*args, **kwargs)

    def mark_as_paid(self, manual: bool = False) -> None:
        self.status = "manual" if manual else "success"
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])
        self.bill.is_paid = True
        self.bill.save(update_fields=["is_paid"])

    def __str__(self) -> str:
        return f"{self.reference} — {self.status}"
