from django.db import models

# Create your models here.
class LabTest(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class LabResult(models.Model):
    lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE)
    patient_name = models.CharField(max_length=100)
    result_value = models.CharField(max_length=100)
    result_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_name} - {self.lab_test.name}"