from django import forms
from django_select2.forms import Select2Widget, ModelSelect2Widget
from .models import LabResult, LabTest
from patient.models import Consultation



class LabTestWidget(ModelSelect2Widget):
    model = LabTest
    search_fields = [
        'name__icontains',
    ]

class ConsultationWidget(ModelSelect2Widget):
    model = Consultation
    search_fields = [
        'patient__name__icontains',
    ]


class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ['lab_test', 'consultation', 'result_name', 'result_value']
        widgets = {
            'lab_test': forms.Select(attrs={'class': 'form-select'}),
            'consultation': forms.Select(attrs={'class': 'form-select'}),
            'result_value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 6.5 mmol/L'}),
            'result_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Blood Glucose'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark these as optional for add forms
        self.fields['consultation'].required = False
        self.fields['lab_test'].required = False
        self.fields['result_name'].required = False
        self.fields['result_value'].required = False

class LabTestForm(forms.ModelForm):
    class Meta:
        model = LabTest 
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter test name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional description'}),
        }
