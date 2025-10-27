from django import forms
from clinicmanager.models import Clinic


class CustomSignupForm(forms.Form):
    clinic_name = forms.CharField(max_length=255, label="Clinic Name")
    clinic_address = forms.CharField(max_length=255, required=False)
    clinic_phone = forms.CharField(max_length=50, required=False)

    def signup(self, request, user):
        """Called automatically by allauth after user signup."""
        Clinic.objects.create(
            name=self.cleaned_data["clinic_name"],
            address=self.cleaned_data.get("clinic_address", ""),
            phone_number=self.cleaned_data.get("clinic_phone", ""),
            created_by=user,
        )
        return user
