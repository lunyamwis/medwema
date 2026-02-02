from django import forms
from .models import (
    SpecialistTask, SonographyStudy, NursingNote,
    ExternalLabRequest, ExternalLabResult,
    HomeVisit, SupplyInvoice, SupplyInvoiceItem,
    DebtCase, DebtFollowUp, EquipmentItem
)


class SpecialistTaskForm(forms.ModelForm):
    class Meta:
        model = SpecialistTask
        fields = ["patient", "consultation", "assigned_to", "role", "service", "notes", "status"]


class SonographyStudyForm(forms.ModelForm):
    class Meta:
        model = SonographyStudy
        fields = ["patient", "consultation", "task", "study_type", "indication", "findings", "impression", "report_file"]


class NursingNoteForm(forms.ModelForm):
    class Meta:
        model = NursingNote
        fields = ["patient", "consultation", "task", "category", "note"]


class ExternalLabRequestForm(forms.ModelForm):
    class Meta:
        model = ExternalLabRequest
        fields = ["patient", "consultation", "lab_name", "lab_email", "subject", "message"]


class ExternalLabResultForm(forms.ModelForm):
    class Meta:
        model = ExternalLabResult
        fields = ["uploaded_file", "notes"]


class HomeVisitForm(forms.ModelForm):
    class Meta:
        model = HomeVisit
        fields = ["patient", "consultation", "visit_date", "address", "purpose", "clinician", "status", "notes"]


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
