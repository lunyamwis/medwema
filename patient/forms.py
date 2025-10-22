# clinic/forms.py
from django import forms
from .models import Patient

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
