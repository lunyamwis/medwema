from django import forms
from django_select2.forms import ModelSelect2Widget

from emr.models import LabResult, LabTest
from patient.models import Consultation, Doctor, Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "name", "date_of_birth", "gender", "blood_group",
            "phone_number", "email", "address",
            "emergency_contact_name", "emergency_contact_phone",
            "doctor",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"autofocus": True, "placeholder": "Full name"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "phone_number": forms.TextInput(attrs={"placeholder": "+254..."}),
            "email": forms.EmailInput(attrs={"placeholder": "patient@email.com"}),
            "address": forms.TextInput(attrs={"placeholder": "Street, Town"}),
            "emergency_contact_name": forms.TextInput(attrs={"placeholder": "Next of kin name"}),
            "emergency_contact_phone": forms.TextInput(attrs={"placeholder": "+254..."}),
            "doctor": ModelSelect2Widget(
                model=Doctor,
                search_fields=["name__icontains"],
                attrs={"data-placeholder": "Search doctor...", "data-minimum-input-length": 0},
            ),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clinic:
            self.fields["doctor"].widget.queryset = Doctor.objects.filter(clinic=clinic)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = f"{existing} form-select".strip()
            else:
                field.widget.attrs["class"] = f"{existing} form-control".strip()


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = [
            "chief_complaints", "history_of_presenting_illness",
            "past_medical_history", "past_surgical_history",
            "drug_allergies", "current_medication", "comorbid_factors",
            "sexual_history", "family_planning_history", "vaccination_history",
            "temperature", "blood_pressure", "pulse", "spo2",
            "respiration_rate", "weight",
            "general_examination", "heent", "cns", "pa", "mss", "rr", "cvs",
            "imaging", "image_findings", "laboratory", "lab_findings",
            "diagnosis", "management", "medication",
            "return_date", "labor_charges",
        ]
        labels = {"pa": "PA / Genitals"}
        widgets = {
            "chief_complaints": forms.Textarea(attrs={"rows": 3}),
            "history_of_presenting_illness": forms.Textarea(attrs={"rows": 3}),
            "past_medical_history": forms.Textarea(attrs={"rows": 2}),
            "past_surgical_history": forms.Textarea(attrs={"rows": 2}),
            "drug_allergies": forms.Textarea(attrs={"rows": 2}),
            "current_medication": forms.Textarea(attrs={"rows": 2}),
            "comorbid_factors": forms.Textarea(attrs={"rows": 2}),
            "sexual_history": forms.Textarea(attrs={"rows": 2}),
            "family_planning_history": forms.Textarea(attrs={"rows": 2}),
            "vaccination_history": forms.Textarea(attrs={"rows": 2}),
            "temperature": forms.NumberInput(attrs={"step": "0.1", "placeholder": "°C"}),
            "blood_pressure": forms.TextInput(attrs={"placeholder": "120/80"}),
            "pulse": forms.NumberInput(attrs={"placeholder": "bpm"}),
            "spo2": forms.NumberInput(attrs={"step": "0.1", "placeholder": "%"}),
            "respiration_rate": forms.NumberInput(attrs={"placeholder": "breaths/min"}),
            "weight": forms.NumberInput(attrs={"step": "0.1", "placeholder": "kg"}),
            "general_examination": forms.Textarea(attrs={"rows": 2}),
            "image_findings": forms.Textarea(attrs={"rows": 2}),
            "lab_findings": forms.Textarea(attrs={"rows": 2}),
            "diagnosis": forms.Textarea(attrs={"rows": 3}),
            "medication": forms.Textarea(attrs={"rows": 3}),
            "return_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "labor_charges": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
            existing = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = f"{existing} form-select".strip()
            else:
                field.widget.attrs["class"] = f"{existing} form-control".strip()


class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ["lab_test", "result_name", "result_value"]
        widgets = {
            "lab_test": ModelSelect2Widget(
                model=LabTest,
                search_fields=["name__icontains"],
                attrs={"data-placeholder": "Search test...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "result_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Blood Glucose"}),
            "result_value": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Enter result value"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
