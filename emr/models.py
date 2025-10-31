from django.db import models
from patient.models import Consultation

# Create your models here.
class LabTest(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class LabResult(models.Model):
    lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE, null=True, blank=True)
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, null=True, blank=True)
    result_name = models.CharField(max_length=100, null=True, blank=True)
    result_value = models.CharField(max_length=100)
    result_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.consultation.patient.name} - {self.lab_test.name}"