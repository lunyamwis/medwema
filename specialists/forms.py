from django import forms
from django.core.exceptions import ValidationError
from django_select2.forms import ModelSelect2Widget

from authentication.models import User
from patient.models import Consultation, Patient
from specialists.models import (
    DebtFollowUp,
    EquipmentItem,
    ExternalLabRequest,
    ExternalLabResult,
    HomeVisit,
    NursingNote,
    ServiceCatalog,
    SpecialistTask,
    SonographyStudy,
    SupplyInvoice,
)


def _apply_bs(form):
    for field in form.fields.values():
        existing = field.widget.attrs.get("class", "")
        if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
            field.widget.attrs["class"] = f"{existing} form-select".strip()
        elif isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs["class"] = f"{existing} form-check-input".strip()
        else:
            field.widget.attrs["class"] = f"{existing} form-control".strip()


class PatientSelectMixin(forms.Form):
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.none(),
        widget=ModelSelect2Widget(
            model=Patient,
            search_fields=["name__icontains", "phone_number__icontains"],
            attrs={"data-placeholder": "Search patient...", "data-minimum-input-length": 1, "class": "form-select"},
        ),
        required=True,
    )
    consultation = forms.ModelChoiceField(
        queryset=Consultation.objects.none(),
        required=False,
        widget=ModelSelect2Widget(
            model=Consultation,
            search_fields=["patient__name__icontains"],
            attrs={"data-placeholder": "Link consultation (optional)...", "data-minimum-input-length": 0, "class": "form-select"},
        ),
    )

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clinic:
            patient_qs = Patient.objects.filter(clinic=clinic, is_active=True)
            consultation_qs = Consultation.objects.filter(patient__clinic=clinic)
            self.fields["patient"].queryset = patient_qs
            self.fields["patient"].widget.queryset = patient_qs
            self.fields["consultation"].queryset = consultation_qs
            self.fields["consultation"].widget.queryset = consultation_qs


class SpecialistTaskForm(PatientSelectMixin, forms.ModelForm):
    class Meta:
        model = SpecialistTask
        fields = ["patient", "consultation", "assigned_to", "role", "service", "notes", "status"]
        widgets = {
            "assigned_to": ModelSelect2Widget(
                model=User,
                search_fields=["first_name__icontains", "last_name__icontains", "username__icontains"],
                attrs={"data-placeholder": "Assign to...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "role": forms.Select(attrs={"class": "form-select"}),
            "service": ModelSelect2Widget(
                model=ServiceCatalog,
                search_fields=["name__icontains"],
                attrs={"data-placeholder": "Search service...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, clinic=clinic, **kwargs)
        if clinic:
            service_qs = ServiceCatalog.objects.filter(clinic=clinic, is_active=True)
            staff_qs = User.objects.filter(clinics=clinic, is_active=True)
            self.fields["service"].queryset = service_qs
            self.fields["service"].widget.queryset = service_qs
            self.fields["assigned_to"].queryset = staff_qs
            self.fields["assigned_to"].widget.queryset = staff_qs
        else:
            all_active = User.objects.filter(is_active=True)
            self.fields["assigned_to"].queryset = all_active
            self.fields["assigned_to"].widget.queryset = all_active


class SonographyStudyForm(PatientSelectMixin, forms.ModelForm):
    class Meta:
        model = SonographyStudy
        fields = ["patient", "consultation", "task", "study_type", "indication", "findings", "impression", "report_file"]
        widgets = {
            "study_type": forms.Select(attrs={"class": "form-select"}),
            "indication": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "findings": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "impression": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, clinic=clinic, **kwargs)
        _apply_bs(self)


class NursingNoteForm(PatientSelectMixin, forms.ModelForm):
    class Meta:
        model = NursingNote
        fields = ["patient", "consultation", "task", "category", "note"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, clinic=clinic, **kwargs)
        _apply_bs(self)


class ExternalLabRequestForm(PatientSelectMixin, forms.ModelForm):
    class Meta:
        model = ExternalLabRequest
        fields = ["patient", "consultation", "lab_name", "lab_email", "subject", "message"]
        widgets = {
            "lab_name": forms.TextInput(attrs={"class": "form-control"}),
            "lab_email": forms.EmailInput(attrs={"class": "form-control"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, clinic=clinic, **kwargs)


class ExternalLabResultForm(forms.ModelForm):
    class Meta:
        model = ExternalLabResult
        fields = ["uploaded_file", "notes"]
        widgets = {
            "uploaded_file": forms.FileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class HomeVisitForm(PatientSelectMixin, forms.ModelForm):
    class Meta:
        model = HomeVisit
        fields = ["patient", "consultation", "visit_date", "address", "purpose", "clinician", "status", "notes"]
        widgets = {
            "visit_date": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}, format="%Y-%m-%dT%H:%M"),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "purpose": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "clinician": ModelSelect2Widget(
                model=User,
                search_fields=["first_name__icontains", "last_name__icontains"],
                attrs={"data-placeholder": "Assign clinician...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, clinic=clinic, **kwargs)
        clinician_qs = (
            User.objects.filter(clinics=clinic, is_active=True)
            if clinic
            else User.objects.filter(is_active=True)
        )
        self.fields["clinician"].queryset = clinician_qs
        self.fields["clinician"].widget.queryset = clinician_qs


class SupplyInvoiceForm(forms.ModelForm):
    class Meta:
        model = SupplyInvoice
        fields = ["vendor", "invoice_number", "invoice_date", "total_amount", "attachment"]
        widgets = {
            "vendor": forms.TextInput(attrs={"class": "form-control"}),
            "invoice_number": forms.TextInput(attrs={"class": "form-control"}),
            "invoice_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "total_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "attachment": forms.FileInput(attrs={"class": "form-control"}),
        }


class EquipmentItemForm(forms.ModelForm):
    class Meta:
        model = EquipmentItem
        fields = ["name", "category", "qty_available", "reorder_level", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "qty_available": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "reorder_level": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class DebtFollowUpForm(forms.ModelForm):
    class Meta:
        model = DebtFollowUp
        fields = ["channel", "message", "sent_to"]
        widgets = {
            "channel": forms.Select(attrs={"class": "form-select"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "sent_to": forms.TextInput(attrs={"class": "form-control"}),
        }
