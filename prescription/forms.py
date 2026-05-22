from django import forms
from django.forms import inlineformset_factory

from django_select2.forms import ModelSelect2Widget

from inventory.models import Item
from patient.models import Consultation
from prescription.models import Prescription


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ["item", "quantity", "dosage", "frequency", "duration", "instructions"]
        widgets = {
            "item": ModelSelect2Widget(
                model=Item,
                search_fields=["name__icontains"],
                attrs={"data-placeholder": "Search medicine by name...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "dosage": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 500mg"}),
            "frequency": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Twice daily"}),
            "duration": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 7 days"}),
            "instructions": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Take after meals..."}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clinic:
            qs = Item.objects.filter(clinic=clinic, is_active=True)
            self.fields["item"].queryset = qs
            self.fields["item"].widget.queryset = qs


PrescriptionFormSet = inlineformset_factory(
    Consultation,
    Prescription,
    form=PrescriptionForm,
    extra=1,
    can_delete=True,
)
