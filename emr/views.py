from __future__ import annotations

import logging

from django.contrib import messages

logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.forms import modelformset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST
from weasyprint import HTML

from emr.forms import LabResultForm
from emr.models import Lab, LabQueue, LabResult, LabTest
from emr.services import lab_queue_complete, lab_queue_start
from emr.services import send_to_lab as send_to_lab_service
from patient.models import Consultation, Patient, Queue


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_clinic(user):
    """Return the clinic this user belongs to (last one, if staff of multiple)."""
    return user.clinics.select_related().last()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def lab_dashboard(request):
    clinic = _get_clinic(request.user)

    # Active queue — all waiting/in_progress items for this clinic
    lab_queue = (
        LabQueue.objects
        .filter(clinic=clinic, status__in=["waiting", "in_progress"])
        .select_related("patient", "lab_test", "consultation")
        .order_by("created_at")
    )

    # History filters
    patient_query   = request.GET.get("patient", "").strip()
    lab_test_query  = request.GET.get("lab_test", "").strip()
    date_from_raw   = request.GET.get("date_from", "").strip()
    date_to_raw     = request.GET.get("date_to", "").strip()

    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to   = parse_date(date_to_raw)   if date_to_raw   else None

    history_qs = (
        LabResult.objects
        .filter(consultation__patient__clinic=clinic)
        .select_related("lab_test", "consultation__patient")
        .order_by("-result_date", "-id")
    )

    filters = Q()
    if patient_query:
        filters &= Q(consultation__patient__name__icontains=patient_query)
    if lab_test_query:
        filters &= Q(lab_test__name__icontains=lab_test_query)
    if date_from:
        filters &= Q(result_date__date__gte=date_from)
    if date_to:
        filters &= Q(result_date__date__lte=date_to)
    if filters:
        history_qs = history_qs.filter(filters)

    history_paginator = Paginator(history_qs, 15)
    history_page_obj  = history_paginator.get_page(request.GET.get("page"))

    return render(request, "emr/dashboard.html", {
        "lab_queue":        lab_queue,
        "history_page_obj": history_page_obj,
        "patient_query":    patient_query,
        "lab_test_query":   lab_test_query,
        "date_from":        date_from_raw,
        "date_to":          date_to_raw,
    })


# ---------------------------------------------------------------------------
# Add lab results (enter results for pending queue items)
# ---------------------------------------------------------------------------

@login_required
def add_lab_result(request, consultation_id):
    clinic = _get_clinic(request.user)
    consultation = get_object_or_404(
        Consultation.objects.select_related("patient", "doctor"),
        id=consultation_id,
        patient__clinic=clinic,
    )

    lab_queue_items = (
        LabQueue.objects
        .filter(consultation=consultation, status__in=["waiting", "in_progress"])
        .select_related("lab_test")
    )

    LabResultFormSet = modelformset_factory(
        LabResult,
        form=LabResultForm,
        extra=max(len(lab_queue_items), 1),
        can_delete=False,
    )

    if request.method == "POST":
        formset = LabResultFormSet(request.POST, queryset=LabResult.objects.none())
        if formset.is_valid():
            saved = []
            for form in formset:
                if not form.has_changed():
                    continue
                instance = form.save(commit=False)
                if not instance.result_value:
                    continue
                instance.consultation = consultation
                # If the lab_test widget was not used, fall back to the matching queue item
                if not instance.lab_test_id:
                    idx = formset.forms.index(form)
                    if idx < len(lab_queue_items):
                        instance.lab_test = lab_queue_items[idx].lab_test
                instance.save()
                saved.append(instance)

            if saved:
                consultation.lab_findings = "; ".join(
                    f"{r.lab_test.name if r.lab_test else '?'}: {r.result_value}"
                    for r in saved
                )
                consultation.save(update_fields=["lab_findings"])
                logger.info("Lab results saved for consultation %s: %d result(s) by %s", consultation.id, len(saved), request.user.username)

            messages.success(request, "Lab results saved successfully.")
            return redirect("lab_dashboard")
    else:
        # Pre-populate lab_test for each form based on queue items
        initial = []
        for item in lab_queue_items:
            initial.append({"lab_test": item.lab_test})
        formset = LabResultFormSet(queryset=LabResult.objects.none(), initial=initial)

    return render(request, "emr/add_result.html", {
        "formset":      formset,
        "consultation": consultation,
        "lab_tests":    lab_queue_items,
    })


# ---------------------------------------------------------------------------
# Edit existing lab results
# ---------------------------------------------------------------------------

@login_required
def edit_lab_results(request, consultation_id):
    clinic = _get_clinic(request.user)
    consultation = get_object_or_404(
        Consultation.objects.select_related("patient", "doctor"),
        id=consultation_id,
        patient__clinic=clinic,
    )
    existing_qs = LabResult.objects.filter(consultation=consultation).select_related("lab_test")

    LabResultFormSet = modelformset_factory(
        LabResult,
        form=LabResultForm,
        extra=0,
        can_delete=True,
    )

    if request.method == "POST":
        formset = LabResultFormSet(request.POST, queryset=existing_qs)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                if not instance.consultation_id:
                    instance.consultation = consultation
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            logger.info("Lab results updated for consultation %s by %s", consultation.id, request.user.username)
            messages.success(
                request,
                f"Lab results for {consultation.patient.name} updated successfully.",
            )
            return redirect("lab_dashboard")
        else:
            logger.warning("Lab result edit form invalid for consultation %s: %s", consultation.id, formset.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        formset = LabResultFormSet(queryset=existing_qs)

    return render(request, "emr/edit_results.html", {
        "formset":      formset,
        "consultation": consultation,
    })


# ---------------------------------------------------------------------------
# View lab results
# ---------------------------------------------------------------------------

@login_required
def view_lab_results(request, consultation_id):
    clinic = _get_clinic(request.user)
    consultation = get_object_or_404(
        Consultation.objects.select_related("patient", "doctor"),
        id=consultation_id,
        patient__clinic=clinic,
    )
    results = (
        LabResult.objects
        .filter(consultation=consultation)
        .select_related("lab_test")
        .order_by("result_date")
    )
    return render(request, "emr/view_results.html", {
        "results":      results,
        "consultation": consultation,
    })


# ---------------------------------------------------------------------------
# Print / PDF
# ---------------------------------------------------------------------------

@login_required
def print_lab_results(request, consultation_id):
    clinic = _get_clinic(request.user)
    consultation = get_object_or_404(
        Consultation.objects.select_related("patient", "doctor"),
        id=consultation_id,
        patient__clinic=clinic,
    )
    results = (
        LabResult.objects
        .filter(consultation=consultation)
        .select_related("lab_test")
        .order_by("result_date")
    )
    html_string = render_to_string("emr/results_pdf.html", {
        "results":      results,
        "consultation": consultation,
        "clinic":       clinic,
    })
    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'filename="lab_results_{consultation_id}.pdf"'
    )
    return response


# ---------------------------------------------------------------------------
# Queue actions
# ---------------------------------------------------------------------------

@login_required
@require_POST
def start_lab_test(request, queue_id):
    clinic = _get_clinic(request.user)
    queue_item = get_object_or_404(LabQueue, id=queue_id, clinic=clinic)
    lab_queue_start(lab_queue=queue_item)
    logger.info("Lab test started for patient '%s' (queue %s) by %s", queue_item.patient.name, queue_id, request.user.username)
    messages.success(request, f"Started test for {queue_item.patient.name}.")
    return redirect("add_result", consultation_id=queue_item.consultation_id)


@login_required
@require_POST
def complete_lab_test(request, queue_id):
    clinic = _get_clinic(request.user)
    queue_item = get_object_or_404(LabQueue, id=queue_id, clinic=clinic)
    lab_queue_complete(lab_queue=queue_item)
    logger.info("Lab test completed for patient '%s' (queue %s) by %s", queue_item.patient.name, queue_id, request.user.username)
    messages.success(
        request,
        f"Test for {queue_item.patient.name} marked as complete.",
    )
    return redirect("lab_dashboard")


# ---------------------------------------------------------------------------
# Send to lab
# ---------------------------------------------------------------------------

@login_required
@require_POST
def send_to_lab_view(request, consultation_id, patient_id):
    clinic = _get_clinic(request.user)
    if consultation_id == 0:
        patient = get_object_or_404(Patient, id=patient_id, clinic=clinic)
        consultation = Consultation.objects.create(
            patient=patient,
            doctor=patient.doctor,
            date=timezone.now(),
            chief_complaints="N/A",
        )
    else:
        consultation = get_object_or_404(
            Consultation.objects.select_related("patient", "doctor"),
            id=consultation_id,
            patient__clinic=clinic,
        )
        patient = consultation.patient

    selected_lab_test_ids = request.POST.getlist("lab_tests")
    if not selected_lab_test_ids:
        logger.warning("send_to_lab: no tests selected for consultation %s by %s", consultation_id, request.user.username)
        messages.warning(request, "Please select at least one lab test.")
        if consultation.doctor:
            return redirect("doctor_detail", pk=consultation.doctor.id)
        return redirect("patient_list")

    lab_test_ids = [int(x) for x in selected_lab_test_ids if x.isdigit()]

    doctor_queue = Queue.objects.filter(
        clinic=clinic,
        doctor=consultation.doctor,
        patient=patient,
        status__in=["waiting", "in_progress"],
    ).first()

    send_to_lab_service(
        clinic=clinic,
        patient=patient,
        consultation=consultation,
        lab_test_ids=lab_test_ids,
        doctor_queue=doctor_queue,
    )

    logger.info("Patient '%s' sent to lab for consultation %s by %s (tests: %s)", patient.name, consultation.id, request.user.username, lab_test_ids)
    messages.success(
        request,
        f"{patient.name} has been sent to the lab successfully.",
    )

    if consultation.doctor:
        return redirect("doctor_detail", pk=consultation.doctor.id)
    return redirect("patient_list")


# ---------------------------------------------------------------------------
# AJAX / API
# ---------------------------------------------------------------------------

@login_required
@require_GET
def ajax_consultation_search(request):
    clinic = _get_clinic(request.user)
    q = request.GET.get("q", "").strip()
    if q:
        qs = Consultation.objects.filter(
            patient__clinic=clinic
        ).filter(
            Q(patient__name__icontains=q) | Q(id__icontains=q)
        ).select_related("patient")[:20]
    else:
        qs = Consultation.objects.none()
    return JsonResponse(
        [{"id": obj.pk, "text": str(obj)} for obj in qs],
        safe=False,
    )


@login_required
@require_GET
def ajax_labtest_search(request):
    clinic = _get_clinic(request.user)
    q = request.GET.get("q", "").strip()
    if q:
        qs = LabTest.objects.filter(lab__clinic=clinic, name__icontains=q, is_active=True)[:20]
    else:
        qs = LabTest.objects.none()
    return JsonResponse(
        [{"id": obj.pk, "text": str(obj)} for obj in qs],
        safe=False,
    )


@login_required
def lab_queue_count_api(request):
    clinic = _get_clinic(request.user)
    count = LabQueue.objects.filter(clinic=clinic, status__in=["waiting", "in_progress"]).count()
    return JsonResponse({"count": count})


# ---------------------------------------------------------------------------
# Kept for URL compatibility — redirects to unified dashboard
# ---------------------------------------------------------------------------

@login_required
def lab_results_dashboard(request):
    return redirect("lab_dashboard")


@login_required
def lab_search_dashboard(request):
    return redirect("lab_dashboard")


@login_required
def consultation_search(request):
    """Kept for backward-compat with older templates that hit this endpoint."""
    clinic = _get_clinic(request.user)
    q = request.GET.get("q", "")
    consultations = (
        Consultation.objects
        .filter(patient__clinic=clinic)
        .select_related("patient")
        .filter(patient__name__icontains=q)
        .only("id", "date", "patient__name")[:20]
    )
    data = [
        {"id": c.id, "label": f"{c.patient.name} ({c.date})"}
        for c in consultations
    ]
    return JsonResponse(data, safe=False)


@login_required
def lab_queue_view(request, lab_id):
    """Legacy view kept for URL compatibility."""
    clinic = _get_clinic(request.user)
    lab = get_object_or_404(Lab, id=lab_id, clinic=clinic)
    queue = LabQueue.objects.filter(
        lab=lab, status__in=["waiting", "in_progress"]
    ).order_by("queue_number")
    return render(request, "emr/dashboard.html", {"lab": lab, "lab_queue": queue})
