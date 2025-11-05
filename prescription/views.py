# prescription/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.forms import modelformset_factory
from django.contrib import messages

from prescription.models import Prescription
from .forms import PrescriptionForm
from patient.models import Consultation


def prescription_list(request):
    prescriptions = Prescription.objects.select_related('consultation','item','prescribed_by').all().order_by('-prescribed_at')
    return render(request, 'prescription/prescription_list.html', {'prescriptions': prescriptions})


def prescription_detail(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    return render(request, 'prescription/prescription_detail.html', {
        'prescription': prescription
    })

def add_prescription(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)

    PrescriptionFormSet = modelformset_factory(
        Prescription,
        form=PrescriptionForm,
        extra=1,  # number of empty forms to show
        can_delete=False
    )

    if request.method == 'POST':
        formset = PrescriptionFormSet(request.POST, queryset=Prescription.objects.none())
        if formset.is_valid():
            prescriptions = formset.save(commit=False)
            for p in prescriptions:
                p.consultation = consultation
                p.prescribed_by = request.user
                p.save()
            messages.success(request, f"{len(prescriptions)} prescriptions added successfully.")
            return redirect('consultation_detail', consultation_id=consultation.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        formset = PrescriptionFormSet(queryset=Prescription.objects.none())

    return render(request, 'prescription/add_prescription.html', {
        'formset': formset,
        'consultation': consultation,
    })
