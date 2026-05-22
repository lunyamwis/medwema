# prescription/views.py
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from prescription.models import Prescription
from .forms import PrescriptionForm, PrescriptionFormSet
from patient.models import Consultation

logger = logging.getLogger(__name__)


def _get_clinic(user):
    return user.clinics.select_related().last()


@login_required
def prescription_list(request):
    clinic = _get_clinic(request.user)
    q = request.GET.get("q", "").strip()
    qs = (
        Prescription.objects
        .filter(consultation__patient__clinic=clinic)
        .select_related('consultation__patient', 'item', 'prescribed_by')
        .order_by('-prescribed_at')
    )
    if q:
        qs = qs.filter(
            Q(consultation__patient__name__icontains=q) |
            Q(item__name__icontains=q) |
            Q(prescribed_by__first_name__icontains=q) |
            Q(prescribed_by__last_name__icontains=q)
        )
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, 'prescription/prescription_list.html', {
        'page_obj': page_obj,
        'query': q,
    })


@login_required
def prescription_detail(request, pk):
    clinic = _get_clinic(request.user)
    prescription = get_object_or_404(
        Prescription.objects.select_related('consultation__patient', 'item', 'prescribed_by'),
        pk=pk,
        consultation__patient__clinic=clinic,
    )
    return render(request, 'prescription/prescription_detail.html', {
        'prescription': prescription
    })

@login_required
def add_prescription(request, consultation_id):
    clinic = _get_clinic(request.user)
    consultation = get_object_or_404(Consultation, id=consultation_id, patient__clinic=clinic)
    form_kwargs = {"clinic": clinic}

    if request.method == 'POST':
        formset = PrescriptionFormSet(
            request.POST,
            instance=consultation,
            form_kwargs=form_kwargs,
        )
        if formset.is_valid():
            prescriptions = formset.save(commit=False)
            for p in prescriptions:
                p.prescribed_by = request.user
                p.save()
            logger.info("%d prescription(s) added for consultation %s by %s", len(prescriptions), consultation.id, request.user.username)
            messages.success(request, f"{len(prescriptions)} prescription(s) added.")
            return redirect('consultation_detail', consultation_id=consultation.id)
        else:
            logger.warning("Prescription formset invalid for consultation %s: %s", consultation.id, formset.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        formset = PrescriptionFormSet(instance=consultation, form_kwargs=form_kwargs)

    return render(request, 'prescription/add_prescription.html', {
        'formset': formset,
        'consultation': consultation,
    })
