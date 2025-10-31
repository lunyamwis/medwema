from django import forms
from .models import LabResult, LabTest


class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ['lab_test', 'consultation', 'result_value', 'result_name']
        widgets = {
            'lab_test': forms.Select(attrs={'class': 'form-select'}),
            'result_value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 6.5 mmol/L'}),
            'consultation': forms.Select(attrs={'class': 'form-select'}),
            'result_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Blood Glucose'}),
        }

class LabTestForm(forms.ModelForm):
    class Meta:
        model = LabTest
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter test name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional description'}),
        }
