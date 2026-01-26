from django import forms
from .models import Bill

class BillEditForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ["total_amount"]
        widgets = {
            "total_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            )
        }
