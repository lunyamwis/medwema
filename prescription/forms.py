# prescription/forms.py
from django import forms
from .models import Prescription
from inventory.models import Item

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['item','quantity','instructions']
        widgets = {
            'item': forms.Select(attrs={'class':'form-control'}),
            'quantity': forms.NumberInput(attrs={'class':'form-control','min':1}),
            'instructions': forms.Textarea(attrs={'rows':2,'class':'form-control'}),
        }
