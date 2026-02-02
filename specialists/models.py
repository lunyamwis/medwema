from django.db import models
from django.conf import settings
from django.utils import timezone
from clinicmanager.models import Clinic
from patient.models import Patient, Consultation
from billing.models import Bill, BillItem

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
    role = models.CharField(max_length=30, choices=SpecialistRole.choices, default=SpecialistRole.OTHER)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} ({self.role})"


class ServiceCatalog(models.Model):
    """
    Services offered by the clinic/specialists. Used for billing and reporting.
    """
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="service_catalog")
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=30, choices=SpecialistRole.choices, default=SpecialistRole.OTHER)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.clinic}"


class NotificationForSpecialist(models.Model):
    """
    Simple in-app alert (dashboard badge). You can later push to email/SMS/WhatsApp providers.
    """
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="notificationspecialist")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notificationspecialist")
    title = models.CharField(max_length=200)
    message = models.TextField()
    url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} -> {self.recipient}"


class SpecialistTask(models.Model):
    """
    The 'Specialists Area' queue/work item:
    - alert doc, patient, specialist if patient has come
    - service offered
    - billing done
    """
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
    role = models.CharField(max_length=30, choices=SpecialistRole.choices, default=SpecialistRole.OTHER)

    service = models.ForeignKey(ServiceCatalog, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default="waiting")

    bill = models.ForeignKey(Bill, on_delete=models.SET_NULL, null=True, blank=True, related_name="specialist_tasks")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def start(self):
        self.status = "in_progress"
        self.started_at = timezone.now()
        self.save()

    def complete(self):
        self.status = "done"
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.patient} - {self.role} - {self.status}"


# -------- Sonographer --------

class SonographyStudy(models.Model):
    STUDY_TYPE = [
        ("ultrasound", "Ultrasound"),
        ("doppler", "Doppler"),
    ]
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="sonography_studies")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="sonography_studies")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="sonography_studies")
    task = models.ForeignKey(SpecialistTask, on_delete=models.SET_NULL, null=True, blank=True, related_name="sonography_studies")

    study_type = models.CharField(max_length=30, choices=STUDY_TYPE)
    indication = models.TextField(blank=True, null=True)
    findings = models.TextField(blank=True, null=True)
    impression = models.TextField(blank=True, null=True)
    report_file = models.FileField(upload_to="sonography/reports/", blank=True, null=True)

    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sonography_done")
    performed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.patient} - {self.study_type} ({self.performed_at.date()})"


# -------- Nurse / Observation --------

class NursingNote(models.Model):
    CATEGORY = [
        ("observation", "Observation"),
        ("iv", "IV / Fluids"),
        ("acute", "Acute management"),
        ("suturing", "Suturing"),
        ("other", "Other"),
    ]
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="nursing_notes")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="nursing_notes")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="nursing_notes")
    task = models.ForeignKey(SpecialistTask, on_delete=models.SET_NULL, null=True, blank=True, related_name="nursing_notes")

    category = models.CharField(max_length=30, choices=CATEGORY, default="observation")
    note = models.TextField()
    vitals_snapshot = models.JSONField(blank=True, null=True)  # optional structured vitals
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="nursing_notes_created")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} - {self.category} ({self.created_at.date()})"


# -------- External Lab Requests --------

class ExternalLabRequest(models.Model):
    STATUS = [
        ("draft", "Draft"),
        ("sent", "Sent to external lab"),
        ("received", "Results received"),
        ("closed", "Closed"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="external_lab_requests")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="external_lab_requests")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="external_lab_requests")

    lab_name = models.CharField(max_length=200)
    lab_email = models.EmailField()
    subject = models.CharField(max_length=200, default="External Lab Request")
    message = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="external_lab_requests_created")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.patient} -> {self.lab_name} ({self.status})"


class ExternalLabResult(models.Model):
    request = models.ForeignKey(ExternalLabRequest, on_delete=models.CASCADE, related_name="results")
    uploaded_file = models.FileField(upload_to="external_lab/results/")
    notes = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


# -------- Home Visit --------

class HomeVisit(models.Model):
    STATUS = [
        ("scheduled", "Scheduled"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="home_visits")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="home_visits")
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="home_visits")

    visit_date = models.DateTimeField()
    address = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.TextField(blank=True, null=True)
    clinician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="home_visits")

    status = models.CharField(max_length=20, choices=STATUS, default="scheduled")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


# -------- Supplies invoicing (expenditure) --------

class SupplyInvoice(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="supply_invoices")
    vendor = models.CharField(max_length=200)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    invoice_date = models.DateField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    attachment = models.FileField(upload_to="supplies/invoices/", blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor} - {self.total_amount}"


class SupplyInvoiceItem(models.Model):
    invoice = models.ForeignKey(SupplyInvoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    qty = models.PositiveIntegerField(default=1)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.line_total = self.qty * self.unit_cost
        super().save(*args, **kwargs)


# -------- Debts + follow-up --------

class DebtCase(models.Model):
    """
    Links to an existing Bill. Makes follow-up easier (WhatsApp/email templates).
    """
    STATUS = [
        ("open", "Open"),
        ("promised", "Promised to pay"),
        ("paid", "Paid"),
        ("written_off", "Written off"),
    ]
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="debt_cases")
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name="debt_case")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="debt_cases")

    status = models.CharField(max_length=20, choices=STATUS, default="open")
    next_followup_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def balance(self):
        # if you later compute partial payments, adjust here
        return self.bill.total_amount if not self.bill.is_paid else 0

    def __str__(self):
        return f"DebtCase Bill#{self.bill.id} - {self.status}"


class DebtFollowUp(models.Model):
    CHANNEL = [
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("call", "Phone call"),
        ("sms", "SMS"),
        ("other", "Other"),
    ]
    debt_case = models.ForeignKey(DebtCase, on_delete=models.CASCADE, related_name="followups")
    channel = models.CharField(max_length=20, choices=CHANNEL)
    message = models.TextField()
    sent_to = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


# -------- Dressing / Equipment list --------

class EquipmentItem(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="equipment_items")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, null=True)  # dressing, instrument, device, etc.
    qty_available = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.qty_available})"
