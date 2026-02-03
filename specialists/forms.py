from django import forms
from .models import (
    SpecialistTask, SonographyStudy, NursingNote,
    ExternalLabRequest, ExternalLabResult,
    HomeVisit, SupplyInvoice, SupplyInvoiceItem,
    DebtCase, DebtFollowUp, EquipmentItem, ServiceCatalog
)
from patient.models import Patient, Consultation
from authentication.models import User
from django.core.exceptions import ValidationError

# class SpecialistTaskForm(forms.ModelForm):
    # def __init__(self, *args, clinic=None, **kwargs):
    #     super().__init__(*args, **kwargs)

    #     if clinic:
    #         self.fields["patient"].queryset = Patient.objects.filter(clinic=clinic).order_by("name")[:50]
    #         self.fields["consultation"].queryset = Consultation.objects.filter(clinic=clinic).order_by("-id")[:50]
    #         self.fields["assigned_to"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name")[:50]

    #         # ✅ Cheap labels (no __str__ surprises)
    #         self.fields["patient"].label_from_instance = lambda p: getattr(p, "name", f"Patient #{p.pk}")
    #         self.fields["consultation"].label_from_instance = lambda c: f"Consultation #{c.pk}"
    #         self.fields["assigned_to"].label_from_instance = lambda u: f"{u.first_name} {u.last_name}".strip() or u.username

    # class Meta:
    #     model = SpecialistTask
    #     fields = ["patient", "consultation", "assigned_to", "role", "service", "notes", "status"]



class SpecialistTaskForm(forms.ModelForm):
    patient_id = forms.IntegerField(label="Patient ID")
    consultation_id = forms.IntegerField(label="Consultation ID", required=False)

    class Meta:
        model = SpecialistTask
        fields = ["patient_id", "consultation_id", "assigned_to", "role", "service", "notes", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # keep these light (small tables)
        self.fields["assigned_to"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        self.fields["service"].queryset = ServiceCatalog.objects.all()

    def clean_patient_id(self):
        pid = self.cleaned_data["patient_id"]
        qs = Patient.objects.filter(pk=pid)
       
        if not qs.exists():
            raise ValidationError("Patient not found for this clinic.")
        return pid

    def clean_consultation_id(self):
        cid = self.cleaned_data.get("consultation_id")
        if not cid:
            return None
        qs = Consultation.objects.filter(pk=cid)
        
        if not qs.exists():
            raise ValidationError("Consultation not found for this clinic.")
        return cid

    def save(self, commit=True):
        obj = super().save(commit=False)

        # attach real FKs
        obj.patient_id = self.cleaned_data["patient_id"]
        obj.consultation_id = self.cleaned_data.get("consultation_id")

        if commit:
            obj.save()
        return obj




class PatientConsultationLightMixin(forms.ModelForm):
    patient_id = forms.IntegerField(label="Patient ID")
    consultation_id = forms.IntegerField(label="Consultation ID", required=False)

    def __init__(self, *args, clinic=None, **kwargs):
        self.clinic = clinic
        super().__init__(*args, **kwargs)

    def clean_patient_id(self):
        pid = self.cleaned_data["patient_id"]
        qs = Patient.objects.filter(pk=pid)
        if self.clinic:
            qs = qs.filter(clinic=self.clinic)
        if not qs.exists():
            raise ValidationError("Patient not found for this clinic.")
        return pid

    def clean_consultation_id(self):
        cid = self.cleaned_data.get("consultation_id")
        if not cid:
            return None
        qs = Consultation.objects.filter(pk=cid)
        if self.clinic:
            qs = qs.filter(clinic=self.clinic)
        if not qs.exists():
            raise ValidationError("Consultation not found for this clinic.")
        return cid

    def attach_patient_consultation(self, obj):
        obj.patient_id = self.cleaned_data["patient_id"]
        obj.consultation_id = self.cleaned_data.get("consultation_id")
        return obj


class SonographyStudyForm(PatientConsultationLightMixin, forms.ModelForm):
    class Meta:
        model = SonographyStudy
        fields = [
            "patient_id", "consultation_id",
            "task", "study_type", "indication",
            "findings", "impression", "report_file"
        ]

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj = self.attach_patient_consultation(obj)
        if commit:
            obj.save()
        return obj


class NursingNoteForm(PatientConsultationLightMixin, forms.ModelForm):
    class Meta:
        model = NursingNote
        fields = ["patient_id", "consultation_id", "task", "category", "note"]

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj = self.attach_patient_consultation(obj)
        if commit:
            obj.save()
        return obj


class ExternalLabRequestForm(PatientConsultationLightMixin, forms.ModelForm):
    class Meta:
        model = ExternalLabRequest
        fields = [
            "patient_id", "consultation_id",
            "lab_name", "lab_email", "subject", "message"
        ]

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj = self.attach_patient_consultation(obj)
        if commit:
            obj.save()
        return obj


class ExternalLabResultForm(forms.ModelForm):
    class Meta:
        model = ExternalLabResult
        fields = ["uploaded_file", "notes"]

class HomeVisitForm(PatientConsultationLightMixin, forms.ModelForm):
    class Meta:
        model = HomeVisit
        fields = [
            "patient_id", "consultation_id",
            "visit_date", "address", "purpose",
            "clinician", "status", "notes"
        ]

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj = self.attach_patient_consultation(obj)
        if commit:
            obj.save()
        return obj

class SupplyInvoiceForm(forms.ModelForm):
    class Meta:
        model = SupplyInvoice
        fields = ["vendor", "invoice_number", "invoice_date", "total_amount", "attachment"]


class EquipmentItemForm(forms.ModelForm):
    class Meta:
        model = EquipmentItem
        fields = ["name", "category", "qty_available", "reorder_level", "notes"]


class DebtFollowUpForm(forms.ModelForm):
    class Meta:
        model = DebtFollowUp
        fields = ["channel", "message", "sent_to"]
