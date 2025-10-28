from django.db import models
from authentication.models import User
from clinicmanager.models import Clinic
# starting


class Doctor(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="doctors", null=True, blank=True)
    name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"Dr. {self.name}"


class Patient(models.Model):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="patients", null=True, blank=True)
    name = models.CharField(max_length=500)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES,default='O')
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    doctor = models.ForeignKey(
        Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name="patients"
    )
    date_registered = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"



class Consultation(models.Model):
    MANAGEMENT_CHOICES = [
        ("supportive", "Supportive"),
        ("preventive", "Preventive"),
        ("counseling", "Counseling"),
        ("referral", "Referral"),
    ]

    IMAGING_CHOICES = [
        ("ultrasound", "Ultrasound"),
        ("chest_xray", "Chest X-ray"),
        ("mri", "MRI"),
        ("ctscan", "CT Scan"),
        ("colonoscopy", "Colonoscopy"),
        ("endoscopy", "Endoscopy"),
        ("barium_meal", "Barium Meal"),
        ("none", "None"),
    ]

    LAB_CHOICES = [
        ("blood_test", "Blood Test"),
        ("swab_test", "Swab Test"),
        ("sputum_test", "Sputum Test"),
        ("urine_test", "Urine Test"),
        ("stool_test", "Stool Test"),
        ("high_vaginal_swab", "High Vaginal Swab Test"),
        ("spermatozoa_test", "Spermatozoa Test"),
        ("ophthalmology_test", "Ophthalmology Test"),
        ("none", "None"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="consultations")
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    # Clinical details
    chief_complaints = models.TextField(blank=True, null=True)
    history_of_presenting_illness = models.TextField(blank=True, null=True)
    past_medical_history = models.TextField(blank=True, null=True)
    past_surgical_history = models.TextField(blank=True, null=True)
    drug_allergies = models.TextField(blank=True, null=True)
    current_medication = models.TextField(blank=True, null=True)
    comorbid_factors = models.TextField(blank=True, null=True)

    # Vitals
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    blood_pressure = models.CharField(max_length=20, blank=True, null=True)
    pulse = models.IntegerField(blank=True, null=True)
    spo2 = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    respiration_rate = models.IntegerField(blank=True, null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    # Examinations
    general_examination = models.TextField(blank=True, null=True)
    heent = models.CharField(max_length=100, blank=True, null=True)
    cns = models.CharField(max_length=100, blank=True, null=True)
    pa = models.CharField(max_length=100, blank=True, null=True)
    mss = models.CharField(max_length=100, blank=True, null=True)
    rr = models.CharField(max_length=100, blank=True, null=True)
    cvs = models.CharField(max_length=100, blank=True, null=True)

    # Investigations (dropdowns)
    imaging = models.CharField(max_length=50, choices=IMAGING_CHOICES, blank=True, null=True)
    image_findings = models.TextField(blank=True, null=True)
    laboratory = models.CharField(max_length=50, choices=LAB_CHOICES, blank=True, null=True)
    lab_findings = models.TextField(blank=True, null=True)

    # Diagnosis & Management
    diagnosis = models.TextField(blank=True, null=True)
    management = models.CharField(max_length=50, choices=MANAGEMENT_CHOICES, blank=True, null=True)

    # Medication & Follow-up
    medication = models.TextField(blank=True, null=True)
    return_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Consultation for {self.patient.name} on {self.date.strftime('%Y-%m-%d')}"
