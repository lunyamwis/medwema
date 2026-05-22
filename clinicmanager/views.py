from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from clinicmanager.models import Clinic


class ClinicSettingsForm(forms.ModelForm):
    class Meta:
        model = Clinic
        fields = ["name", "address", "phone_number", "email", "website", "logo"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
        }


@login_required
def clinic_settings(request):
    clinic = request.user.clinics.select_related().last()
    if clinic is None:
        messages.warning(request, "No clinic associated with your account.")
        return redirect("patient_list")

    if request.method == "POST":
        form = ClinicSettingsForm(request.POST, request.FILES, instance=clinic)
        if form.is_valid():
            form.save()
            messages.success(request, "Clinic settings saved.")
            return redirect("clinic_settings")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ClinicSettingsForm(instance=clinic)

    return render(request, "clinicmanager/settings.html", {"form": form, "clinic": clinic})
