from django import forms
from django.forms import inlineformset_factory
from django_select2.forms import ModelSelect2Widget

from emr.models import LabResult, LabTest
from patient.models import Consultation


class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ["lab_test", "result_name", "result_value"]
        widgets = {
            "lab_test": ModelSelect2Widget(
                model=LabTest,
                search_fields=["name__icontains"],
                attrs={
                    "data-placeholder": "Search test name...",
                    "data-minimum-input-length": 0,
                    "class": "form-select",
                },
            ),
            "result_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Sub-test name (optional)"}),
            "result_value": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Enter result value"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


LabResultFormSet = inlineformset_factory(
    Consultation,
    LabResult,
    form=LabResultForm,
    fk_name="consultation",
    extra=1,
    can_delete=True,
)


class LabTestForm(forms.ModelForm):
    class Meta:
        model = LabTest
        fields = ["name", "category", "unit", "reference_min", "reference_max", "reference_text", "price", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Test name"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. mg/dL"}),
            "reference_min": forms.TextInput(attrs={"class": "form-control", "placeholder": "Min"}),
            "reference_max": forms.TextInput(attrs={"class": "form-control", "placeholder": "Max"}),
            "reference_text": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Negative"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
