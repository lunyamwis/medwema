# clinic/forms.py
from django import forms
from .models import Patient,Consultation


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        exclude = ['patient', 'doctor', 'date']
        labels = {
            'pa': 'PA/GENITALS',
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
            **{f: forms.TextInput(attrs={'class': 'form-control'}) for f in [
                'blood_pressure', 'temperature', 'pulse', 'spo2', 'respiration_rate', 'weight'
            ]}
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
