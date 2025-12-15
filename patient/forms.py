# clinic/forms.py
from django import forms
from .models import Patient,Consultation

from django.forms import inlineformset_factory
from django_select2.forms import Select2Widget
from emr.models import  LabResult, LabTest

class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ['lab_test', 'result_value']
        widgets = {
            'lab_test': Select2Widget(attrs={'class': 'form-select', 'data-placeholder': 'Select a lab test...'}),
            'result_value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter result value'}),
        }

LabResultFormSet = inlineformset_factory(
    Consultation, LabResult, form=LabResultForm,
    extra=1, can_delete=True
)

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        exclude = ['patient', 'doctor', 'date']
        labels = {
            'pa': 'PA/GENITALS',
            'sexual_history': 'SEXUAL HISTORY',
            'family_planning_history': 'FAMILY PLANNING HISTORY',
            'vaccination_history': 'VACCINATION HISTORY',
        }
        widgets = {
            'return_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'chief_complaints': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'history_of_presenting_illness': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'diagnosis': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'medication': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'management': forms.Select(attrs={'class': 'form-select'}),
            'imaging': forms.Select(attrs={'class': 'form-select'}),
            'laboratory': forms.Select(attrs={'class': 'form-select'}),
            'sexual_history': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'family_planning_history': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'vaccination_history': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            **{f: forms.TextInput(attrs={'class': 'form-control'}) for f in [
                'blood_pressure', 'temperature', 'pulse', 'spo2', 'respiration_rate', 'weight'
            ]},
            'labor_charges': forms.TextInput(attrs={'class': 'form-control'}),
            'lab_findings': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.label:
                field.label = field.label.upper()

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "name",
            "date_of_birth",
            "gender",
            "phone_number",
            "email",
            "address",
            "doctor",  # <-- added this field
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }
