from django.db import models
from django.utils import timezone
from patient.models import Consultation, Patient
from clinicmanager.models import Clinic


class Lab(models.Model):
    class LabType(models.TextChoices):
        INTERNAL = "Internal", "Internal (Performed In-House)"
        EXTERNAL = "External", "External (Referral Lab)"

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="labs", null=True, blank=True)
    name = models.CharField(max_length=100, db_index=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    lab_type = models.CharField(max_length=20, choices=LabType.choices, default=LabType.INTERNAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "lab_type"]),
        ]

    def __str__(self) -> str:
        return self.name


class LabTest(models.Model):
    class Category(models.TextChoices):
        TEST = "Test", "Lab Test"
        SCAN = "Scan", "Imaging / Scan"

    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, null=True, blank=True, related_name="tests")
    name = models.CharField(max_length=200, db_index=True)
    category = models.CharField(max_length=80, choices=Category.choices, default=Category.TEST, db_index=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    reference_min = models.CharField(max_length=100, null=True, blank=True)
    reference_max = models.CharField(max_length=100, null=True, blank=True)
    reference_text = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def reference_range_display(self) -> str:
        if self.reference_text:
            return self.reference_text
        if self.reference_min is not None and self.reference_max is not None:
            return f"{self.reference_min} – {self.reference_max} {self.unit or ''}".strip()
        return "N/A"

    def __str__(self) -> str:
        return self.name


class LabResult(models.Model):
    lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE, null=True, blank=True, related_name="results")
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, null=True, blank=True, related_name="lab_results")
    result_name = models.CharField(max_length=100, null=True, blank=True)
    result_value = models.TextField(null=True, blank=True)
    result_date = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-result_date"]
        indexes = [
            models.Index(fields=["consultation", "result_date"]),
            models.Index(fields=["lab_test"]),
        ]

    def is_abnormal(self) -> bool:
        try:
            val = float(self.result_value)
        except (TypeError, ValueError):
            return False
        ref_min = self.lab_test.reference_min if self.lab_test else None
        ref_max = self.lab_test.reference_max if self.lab_test else None
        if ref_min is not None:
            try:
                if val < float(ref_min):
                    return True
            except (TypeError, ValueError):
                pass
        if ref_max is not None:
            try:
                if val > float(ref_max):
                    return True
            except (TypeError, ValueError):
                pass
        return False

    def __str__(self) -> str:
        return f"{self.consultation} — {self.lab_test}"


class LabQueue(models.Model):
    STATUS_CHOICES = [
        ("waiting", "Waiting"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("skipped", "Skipped"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="lab_queues")
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="lab_queues", null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="lab_queues")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_queues")
    lab_test = models.ForeignKey(LabTest, on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_queues")
    queue_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = ("clinic", "lab", "queue_number")
        indexes = [
            models.Index(fields=["clinic", "status"]),
            models.Index(fields=["lab", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.queue_number:
            last = LabQueue.objects.filter(clinic=self.clinic, lab=self.lab).order_by("-queue_number").first()
            self.queue_number = (last.queue_number + 1) if last else 1
        super().save(*args, **kwargs)

    def start(self) -> None:
        self.status = "in_progress"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def complete(self) -> None:
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def __str__(self) -> str:
        test_name = self.lab_test.name if self.lab_test else "N/A"
        return f"{self.patient.name} — {test_name} — #{self.queue_number}"
