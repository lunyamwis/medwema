from django.db import models
from patient.models import Consultation


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
    result_value = models.CharField(max_length=100)
    result_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.consultation.patient.name} - {self.lab_test.name}"

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
