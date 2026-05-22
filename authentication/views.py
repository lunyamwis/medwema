from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from authentication.models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "bio", "profile_picture"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
        }


class PasswordChangeInlineForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput, label="Current password")
    new_password = forms.CharField(widget=forms.PasswordInput, label="New password", min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm new password")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("New passwords do not match.")
        return cleaned


@login_required
def profile_view(request):
    user = request.user
    if request.method == "POST":
        action = request.POST.get("action", "profile")

        if action == "profile":
            form = ProfileForm(request.POST, request.FILES, instance=user)
            pwd_form = PasswordChangeInlineForm()
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("user_profile")
            else:
                messages.error(request, "Please correct the errors below.")

        elif action == "password":
            form = ProfileForm(instance=user)
            pwd_form = PasswordChangeInlineForm(request.POST)
            if pwd_form.is_valid():
                if not user.check_password(pwd_form.cleaned_data["current_password"]):
                    pwd_form.add_error("current_password", "Incorrect current password.")
                else:
                    user.set_password(pwd_form.cleaned_data["new_password"])
                    user.save()
                    messages.success(request, "Password changed successfully. Please log in again.")
                    return redirect("account_login")
        else:
            form = ProfileForm(instance=user)
            pwd_form = PasswordChangeInlineForm()
    else:
        form = ProfileForm(instance=user)
        pwd_form = PasswordChangeInlineForm()

    clinic = user.clinics.select_related().last()
    return render(request, "authentication/profile.html", {
        "form": form,
        "pwd_form": pwd_form,
        "clinic": clinic,
    })
