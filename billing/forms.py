from django import forms

from billing.models import Bill


class BillEditForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ["total_amount", "discount", "notes"]
        widgets = {
            "total_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "discount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
