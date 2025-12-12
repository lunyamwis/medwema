from django.db import models
from django.db import models
from django.utils import timezone
from patient.models import Consultation, Patient
from clinicmanager.models import Clinic





class Lab(models.Model):
    class LabType(models.TextChoices):
        INTERNAL = "Internal", "Internal (Performed In-House)"
        EXTERNAL = "External", "External (Referral Lab)"

    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255, null=True, blank=True)
    lab_type = models.CharField(
        max_length=20,
        choices=LabType.choices,
        default=LabType.INTERNAL,
        help_text="Select whether this lab performs tests in-house or refers them externally."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class LabTest(models.Model):
    class Category(models.TextChoices):
        TEST = "Test", "Lab Test"
        SCAN = "Scan", "Imaging / Scan"

    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=80,
        choices=Category.choices,
        default=Category.TEST,
    )
    unit = models.CharField(max_length=50, null=True, blank=True)
    reference_min = models.CharField(max_length=100, null=True, blank=True, help_text="Lower limit of normal range")
    reference_max = models.CharField(max_length=100, null=True, blank=True, help_text="Upper limit of normal range")
    reference_text = models.CharField(max_length=255, null=True, blank=True, help_text="For textual or complex ranges (e.g., Negative, Non-reactive, Normal)")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def reference_range_display(self):
        """Helper method to show range properly."""
        if self.reference_text:
            return self.reference_text
        if self.reference_min is not None and self.reference_max is not None:
            return f"{self.reference_min} - {self.reference_max} {self.unit or ''}"
        return "N/A"


class LabResult(models.Model):
    lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE, null=True, blank=True)
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, null=True, blank=True)
    result_name = models.CharField(max_length=100, null=True, blank=True)
    result_value = models.TextField(null=True, blank=True)
    result_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.consultation} - {self.lab_test}"

    def is_abnormal(self):
        """
        Checks whether the result is outside the defined normal range.
        Works only for numeric results with reference_min and reference_max.
        """
        try:
            val = float(self.result_value)
        except ValueError:
            return False  # Non-numeric results (e.g., 'Positive') are handled separately

        if self.lab_test.reference_min is not None and val < self.lab_test.reference_min:
            return True
        if self.lab_test.reference_max is not None and val > self.lab_test.reference_max:
            return True
        return False


# emr/models.py (or a new file like lab_queue/models.py)


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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting")

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = ("clinic", "lab", "queue_number")

    def save(self, *args, **kwargs):
        if not self.queue_number:
            last = LabQueue.objects.filter(clinic=self.clinic, lab=self.lab).order_by("-queue_number").first()
            self.queue_number = last.queue_number + 1 if last else 1
        super().save(*args, **kwargs)

    def start(self):
        self.status = "in_progress"
        self.started_at = timezone.now()
        self.save()

    def complete(self):
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.patient.name} - {self.lab_test.name if self.lab_test else 'N/A'} - #{self.queue_number}"
