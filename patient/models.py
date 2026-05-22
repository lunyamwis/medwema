from django.db import models
from django.db.models import Q
from django.utils import timezone
from authentication.models import User
from clinicmanager.models import Clinic


class Doctor(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="doctors", null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="doctor_profile")
    name = models.CharField(max_length=100, db_index=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "name"]),
        ]

    def __str__(self) -> str:
        return f"Dr. {self.name}"


class Patient(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"), ("A-", "A-"),
        ("B+", "B+"), ("B-", "B-"),
        ("AB+", "AB+"), ("AB-", "AB-"),
        ("O+", "O+"), ("O-", "O-"),
        ("unknown", "Unknown"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="patients", null=True, blank=True)
    patient_number = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=500, db_index=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default="O")
    blood_group = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, default="unknown", blank=True, null=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name="patients")
    is_active = models.BooleanField(default=True, db_index=True, null=True, blank=True)
    date_registered = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "name"]),
            models.Index(fields=["clinic", "phone_number"]),
            models.Index(fields=["clinic", "is_active"]),
            models.Index(fields=["date_registered"]),
        ]

    def save(self, *args, **kwargs):
        if not self.patient_number and self.clinic_id:
            last = Patient.objects.filter(clinic_id=self.clinic_id).order_by("-id").first()
            seq = (last.id + 1) if last else 1
            self.patient_number = f"P{self.clinic_id:03d}{seq:05d}"
        super().save(*args, **kwargs)

    def age(self) -> int:
        today = timezone.now().date()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def __str__(self) -> str:
        return self.name


class Consultation(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]
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
    date = models.DateTimeField(default=timezone.now, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active", db_index=True)
    consultation_number = models.CharField(max_length=30, blank=True, null=True, db_index=True)

    # Clinical history
    chief_complaints = models.TextField(blank=True, null=True)
    history_of_presenting_illness = models.TextField(blank=True, null=True)
    past_medical_history = models.TextField(blank=True, null=True)
    past_surgical_history = models.TextField(blank=True, null=True)
    drug_allergies = models.TextField(blank=True, null=True)
    current_medication = models.TextField(blank=True, null=True)
    comorbid_factors = models.TextField(blank=True, null=True)
    sexual_history = models.TextField(blank=True, null=True)
    family_planning_history = models.TextField(blank=True, null=True)
    vaccination_history = models.TextField(blank=True, null=True)

    # Vitals
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    blood_pressure = models.CharField(max_length=20, blank=True, null=True)
    pulse = models.IntegerField(blank=True, null=True)
    spo2 = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    respiration_rate = models.IntegerField(blank=True, null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    # Physical examination
    general_examination = models.TextField(blank=True, null=True)
    heent = models.CharField(max_length=100, blank=True, null=True)
    cns = models.CharField(max_length=100, blank=True, null=True)
    pa = models.CharField(max_length=100, blank=True, null=True)
    mss = models.CharField(max_length=100, blank=True, null=True)
    rr = models.CharField(max_length=100, blank=True, null=True)
    cvs = models.CharField(max_length=100, blank=True, null=True)

    # Investigations
    imaging = models.CharField(max_length=50, choices=IMAGING_CHOICES, blank=True, null=True)
    image_findings = models.TextField(blank=True, null=True)
    laboratory = models.CharField(max_length=50, choices=LAB_CHOICES, blank=True, null=True)
    lab_findings = models.TextField(blank=True, null=True)

    # Diagnosis & management
    diagnosis = models.TextField(blank=True, null=True)
    management = models.CharField(max_length=50, choices=MANAGEMENT_CHOICES, blank=True, null=True)
    medication = models.TextField(blank=True, null=True)
    return_date = models.DateField(blank=True, null=True)
    labor_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["patient", "date"]),
            models.Index(fields=["doctor", "date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["date"]),
        ]

    def save(self, *args, **kwargs):
        if not self.consultation_number and self.patient_id:
            today = timezone.now().strftime("%Y%m%d")
            count = Consultation.objects.filter(date__date=timezone.now().date()).count() + 1
            self.consultation_number = f"C{today}{count:04d}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Consultation for {self.patient.name} on {self.date.strftime('%Y-%m-%d')}"


class Queue(models.Model):
    STATUS_CHOICES = [
        ("waiting", "Waiting"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("skipped", "Skipped"),
        ("inlab", "In Lab"),
        ("fromLab", "From Lab"),
    ]
    PRIORITY_CHOICES = [
        ("normal", "Normal"),
        ("urgent", "Urgent"),
        ("emergency", "Emergency"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="queues")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="queues")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="queues")
    queue_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting", db_index=True, null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="normal", db_index=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["priority", "created_at"]
        indexes = [
            models.Index(fields=["clinic", "status"]),
            models.Index(fields=["doctor", "status"]),
            models.Index(fields=["clinic", "doctor", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.queue_number:
            last = Queue.objects.filter(doctor=self.doctor, clinic=self.clinic).order_by("-queue_number").first()
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
        return f"{self.patient.name} — Dr. {self.doctor.name} — #{self.queue_number} ({self.status})"
