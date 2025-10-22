# patient/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Doctor, Patient
from .forms import PatientForm

def register_patient(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("patient_success")
    else:
        form = PatientForm()
    return render(request, "patient/register_patient.html", {"form": form})


def patient_success(request):
    return render(request, "patient/patient_success.html")



def doctor_detail(request, pk):
    doctor = Doctor.objects.get(pk=pk)
    patients = doctor.patients.all()  # from related_name="patients"
    return render(request, "patient/doctor_detail.html", {"doctor": doctor, "patients": patients})


# List all doctors
def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(request, 'patient/doctor_list.html', {'doctors': doctors})


# Show doctor details and assigned patients
def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    return render(request, 'patient/doctor_detail.html', {'doctor': doctor})


# List all patients
def patient_list(request):
    patients = Patient.objects.select_related('doctor').all()
    return render(request, 'patient/patient_list.html', {'patients': patients})


def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    return render(request, 'patient/patient_detail.html', {'patient': patient})


def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'{patient.name} has been updated successfully!')
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)

    return render(request, 'patient/patient_edit.html', {'form': form, 'patient': patient})
