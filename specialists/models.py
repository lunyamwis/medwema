from django.conf import settings
from django.db import models
from django.utils import timezone

from billing.models import Bill
from clinicmanager.models import Clinic
from patient.models import Consultation, Patient

User = settings.AUTH_USER_MODEL


class SpecialistRole(models.TextChoices):
    SONOGRAPHER = "sonographer", "Sonographer"
    NURSE = "nurse", "Nurse / Observation"
    CARDIOLOGIST = "cardiologist", "Cardiologist"
    RADIOLOGIST = "radiologist", "Radiologist"
    PHYSICIAN = "physician", "Physician"
    OTHER = "other", "Other"


class SpecialistProfile(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="specialist_profiles")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="specialist_profile")
    role = models.CharField(max_length=30, choices=SpecialistRole.choices, default=SpecialistRole.OTHER, db_index=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["clinic", "role"]),
            models.Index(fields=["clinic", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} ({self.get_role_display()})"


class ServiceCatalog(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="service_catalog")
    name = models.CharField(max_length=200, db_index=True)
    role = models.CharField(max_length=30, choices=SpecialistRole.choices, default=SpecialistRole.OTHER, db_index=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "role", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} — {self.clinic}"


class NotificationForSpecialist(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="specialist_notifications")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="specialist_notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    seen = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "seen"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} → {self.recipient}"


class SpecialistTask(models.Model):
    STATUS = [
        ("waiting", "Waiting"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="specialist_tasks")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="specialist_tasks")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="specialist_tasks")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_specialist_tasks")
    role = models.CharField(max_length=30, choices=SpecialistRole.choices, default=SpecialistRole.OTHER, db_index=True)
    service = models.ForeignKey(ServiceCatalog, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default="waiting", db_index=True)
    bill = models.ForeignKey(Bill, on_delete=models.SET_NULL, null=True, blank=True, related_name="specialist_tasks")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clinic", "status"]),
            models.Index(fields=["clinic", "role", "status"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def start(self) -> None:
        self.status = "in_progress"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def complete(self) -> None:
        self.status = "done"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def __str__(self) -> str:
        return f"{self.patient} — {self.get_role_display()} — {self.status}"


class SonographyStudy(models.Model):
    STUDY_TYPE = [("ultrasound", "Ultrasound"), ("doppler", "Doppler")]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="sonography_studies")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="sonography_studies")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="sonography_studies")
    task = models.ForeignKey(SpecialistTask, on_delete=models.SET_NULL, null=True, blank=True, related_name="sonography_studies")
    study_type = models.CharField(max_length=30, choices=STUDY_TYPE, db_index=True)
    indication = models.TextField(blank=True, null=True)
    findings = models.TextField(blank=True, null=True)
    impression = models.TextField(blank=True, null=True)
    report_file = models.FileField(upload_to="sonography/reports/", blank=True, null=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sonography_done")
    performed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self) -> str:
        return f"{self.patient} — {self.study_type} ({self.performed_at.date()})"


class NursingNote(models.Model):
    CATEGORY = [
        ("observation", "Observation"),
        ("iv", "IV / Fluids"),
        ("acute", "Acute Management"),
        ("suturing", "Suturing"),
        ("other", "Other"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="nursing_notes")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="nursing_notes")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="nursing_notes")
    task = models.ForeignKey(SpecialistTask, on_delete=models.SET_NULL, null=True, blank=True, related_name="nursing_notes")
    category = models.CharField(max_length=30, choices=CATEGORY, default="observation", db_index=True)
    note = models.TextField()
    vitals_snapshot = models.JSONField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="nursing_notes_created")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} — {self.get_category_display()} ({self.created_at.date()})"


class ExternalLabRequest(models.Model):
    STATUS = [
        ("draft", "Draft"),
        ("sent", "Sent to External Lab"),
        ("received", "Results Received"),
        ("closed", "Closed"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="external_lab_requests")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="external_lab_requests")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="external_lab_requests")
    lab_name = models.CharField(max_length=200)
    lab_email = models.EmailField()
    subject = models.CharField(max_length=200, default="External Lab Request")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default="draft", db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="external_lab_requests_created")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} → {self.lab_name} ({self.status})"


class ExternalLabResult(models.Model):
    request = models.ForeignKey(ExternalLabRequest, on_delete=models.CASCADE, related_name="results")
    uploaded_file = models.FileField(upload_to="external_lab/results/")
    notes = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_lab_results")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Result for {self.request}"


class HomeVisit(models.Model):
    STATUS = [("scheduled", "Scheduled"), ("done", "Done"), ("cancelled", "Cancelled")]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="home_visits")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="home_visits")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="home_visits")
    visit_date = models.DateTimeField(db_index=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.TextField(blank=True, null=True)
    clinician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="home_visits")
    status = models.CharField(max_length=20, choices=STATUS, default="scheduled", db_index=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-visit_date"]

    def __str__(self) -> str:
        return f"{self.patient} — {self.visit_date.date()} ({self.status})"


class SupplyInvoice(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="supply_invoices")
    vendor = models.CharField(max_length=200, db_index=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    invoice_date = models.DateField(default=timezone.now, db_index=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    attachment = models.FileField(upload_to="supplies/invoices/", blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="supply_invoices_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_date"]

    def __str__(self) -> str:
        return f"{self.vendor} — {self.total_amount}"


class SupplyInvoiceItem(models.Model):
    invoice = models.ForeignKey(SupplyInvoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    qty = models.PositiveIntegerField(default=1)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.line_total = self.qty * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.description} × {self.qty}"


class DebtCase(models.Model):
    STATUS = [
        ("open", "Open"),
        ("promised", "Promised to Pay"),
        ("paid", "Paid"),
        ("written_off", "Written Off"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="debt_cases")
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name="debt_case")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="debt_cases")
    status = models.CharField(max_length=20, choices=STATUS, default="open", db_index=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clinic", "status"]),
        ]

    @property
    def balance(self):
        return self.bill.total_amount if not self.bill.is_paid else 0

    def __str__(self) -> str:
        return f"Debt — Bill #{self.bill.id} ({self.status})"


class DebtFollowUp(models.Model):
    CHANNEL = [
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("call", "Phone Call"),
        ("sms", "SMS"),
        ("other", "Other"),
    ]

    debt_case = models.ForeignKey(DebtCase, on_delete=models.CASCADE, related_name="followups")
    channel = models.CharField(max_length=20, choices=CHANNEL)
    message = models.TextField()
    sent_to = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="debt_followups")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_channel_display()} — {self.debt_case}"


class EquipmentItem(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="equipment_items")
    name = models.CharField(max_length=200, db_index=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    qty_available = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "name"]),
        ]

    def is_low_stock(self) -> bool:
        return self.qty_available <= self.reorder_level

    def __str__(self) -> str:
        return f"{self.name} ({self.qty_available})"
