# prescription/forms.py
from django import forms
from .models import Prescription
from django_select2.forms import ModelSelect2Widget
from inventory.models import Item

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['item','quantity','instructions']
        widgets = {
            'item': ModelSelect2Widget(model=Item, search_fields=['name__icontains']),
            'quantity': forms.NumberInput(attrs={'class':'form-control','min':1}),
            'instructions': forms.Textarea(attrs={'rows':2,'class':'form-control'}),
        }
