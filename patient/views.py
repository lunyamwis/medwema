from __future__ import annotations

import json
import logging
import os
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q as DQ
from django.utils import timezone

logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from billing.models import Bill
from billing.services import bill_add_item, bill_get_or_create
from emr.models import LabTest
from patient.forms import ConsultationForm, PatientForm
from patient.models import Consultation, Doctor, Patient, Queue
from patient.selectors import (
    consultation_get,
    consultation_list,
    consultation_list_for_patient,
    doctor_get,
    doctor_list,
    patient_get,
    patient_list,
    queue_list_active,
    queue_waiting_count,
    queue_completed_count,
)
from patient.services import (
    consultation_create,
    consultation_update,
    patient_create,
    patient_update,
    queue_add_patient,
)


def _get_clinic(user):
    return user.clinics.select_related().last()


# ─── Speech-to-Consultation ───────────────────────────────────────────────────

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def speech_to_consultation(request, patient_id):
    clinic = _get_clinic(request.user)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("speech_to_consultation: invalid JSON body for patient %s", patient_id)
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    transcript = data.get("transcript", "").strip()
    if not transcript:
        return JsonResponse({"error": "Transcript is required."}, status=400)

    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "consultation_schema.json")
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except FileNotFoundError:
        logger.error("speech_to_consultation: schema file not found at %s", schema_path)
        return JsonResponse({"error": "Schema file not found."}, status=500)

    try:
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a medical scribe. Extract consultation data from the speech transcript "
                        f"into valid JSON matching exactly this schema: {json.dumps(schema)}. "
                        "Return only the JSON object, nothing else."
                    ),
                },
                {"role": "user", "content": f"Transcript:\n{transcript}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        consultation_data = json.loads(response.choices[0].message.content)
    except Exception as exc:
        logger.error("speech_to_consultation: OpenAI error for patient %s: %s", patient_id, exc, exc_info=True)
        return JsonResponse({"error": str(exc)}, status=500)

    patient = get_object_or_404(Patient, id=patient_id, clinic=clinic)
    try:
        fields = {}
        fields.update(consultation_data.get("clinical_details") or {})
        fields.update(consultation_data.get("vitals") or {})
        fields.update(consultation_data.get("examinations") or {})
        fields.update(consultation_data.get("investigations") or {})
        fields.update(consultation_data.get("diagnosis_management") or {})
        # Remove null values so model defaults apply
        fields = {k: v for k, v in fields.items() if v is not None}
        consultation = Consultation.objects.create(patient=patient, doctor=patient.doctor, **fields)
        logger.info("speech_to_consultation: consultation %s created for patient %s", consultation.id, patient_id)
    except Exception as exc:
        logger.error("speech_to_consultation: DB save failed for patient %s: %s", patient_id, exc, exc_info=True)
        return JsonResponse({"error": f"Failed to save consultation: {exc}"}, status=500)

    return JsonResponse({
        "success": True,
        "consultation_id": consultation.id,
        "message": "Consultation created from speech.",
    })


# ─── Patients ─────────────────────────────────────────────────────────────────

@login_required
def patient_list_view(request):
    clinic = _get_clinic(request.user)
    query = request.GET.get("q", "").strip()
    qs = patient_list(clinic=clinic, search=query)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    doctors = doctor_list(clinic=clinic)

    today = timezone.localdate()
    last_7 = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

    reg_rows = (
        Patient.objects.filter(
            clinic=clinic,
            date_registered__date__gte=last_7[0],
            date_registered__date__lte=today,
        )
        .values("date_registered__date")
        .annotate(count=Count("id"))
    )
    reg_map = {row["date_registered__date"]: row["count"] for row in reg_rows}
    reg_chart_labels = json.dumps([d.strftime("%b %d") for d in last_7])
    reg_chart_data = json.dumps([reg_map.get(d, 0) for d in last_7])

    gender_rows = (
        Patient.objects.filter(clinic=clinic)
        .values("gender")
        .annotate(count=Count("id"))
        .order_by("gender")
    )
    gender_map = {"M": "Male", "F": "Female", "O": "Other"}
    gender_labels = json.dumps([gender_map.get(r["gender"], r["gender"]) for r in gender_rows])
    gender_data = json.dumps([r["count"] for r in gender_rows])

    total_patients = Patient.objects.filter(clinic=clinic).count()
    doctors_count = Doctor.objects.filter(clinic=clinic).count()

    return render(request, "patient/patient_list.html", {
        "page_obj": page_obj,
        "query": query,
        "doctors": doctors,
        "waiting_count": queue_waiting_count(clinic=clinic),
        "completed_count": queue_completed_count(clinic=clinic),
        "total_patients": total_patients,
        "doctors_count": doctors_count,
        "reg_chart_labels": reg_chart_labels,
        "reg_chart_data": reg_chart_data,
        "gender_labels": gender_labels,
        "gender_data": gender_data,
    })


@login_required
def register_patient(request):
    clinic = _get_clinic(request.user)
    if request.method == "POST":
        form = PatientForm(request.POST, clinic=clinic)
        if form.is_valid():
            d = form.cleaned_data
            patient = patient_create(
                clinic=clinic,
                name=d["name"],
                date_of_birth=d["date_of_birth"],
                gender=d["gender"],
                phone_number=d["phone_number"],
                email=d.get("email", ""),
                address=d.get("address", ""),
                blood_group=d.get("blood_group", "unknown"),
                emergency_contact_name=d.get("emergency_contact_name", ""),
                emergency_contact_phone=d.get("emergency_contact_phone", ""),
                doctor=d.get("doctor"),
            )
            logger.info("Patient '%s' (id=%s) registered by %s", patient.name, patient.pk, request.user.username)
            messages.success(request, f"Patient {patient.name} registered successfully.")
            return redirect("patient_detail", pk=patient.pk)
    else:
        form = PatientForm(clinic=clinic)
    return render(request, "patient/register_patient.html", {"form": form})


@login_required
def patient_detail(request, pk):
    clinic = _get_clinic(request.user)
    patient = patient_get(pk=pk, clinic=clinic)
    consultations = consultation_list_for_patient(patient=patient)[:5]
    return render(request, "patient/patient_detail.html", {
        "patient": patient,
        "consultations": consultations,
    })


@login_required
def patient_edit(request, pk):
    clinic = _get_clinic(request.user)
    patient = patient_get(pk=pk, clinic=clinic)
    if request.method == "POST":
        form = PatientForm(request.POST, instance=patient, clinic=clinic)
        if form.is_valid():
            patient_update(patient=patient, **form.cleaned_data)
            logger.info("Patient '%s' (id=%s) updated by %s", patient.name, patient.pk, request.user.username)
            messages.success(request, f"{patient.name} updated successfully.")
            return redirect("patient_detail", pk=patient.pk)
    else:
        form = PatientForm(instance=patient, clinic=clinic)
    return render(request, "patient/patient_edit.html", {"form": form, "patient": patient})


@login_required
def patient_consultations(request, patient_id):
    clinic = _get_clinic(request.user)
    patient = patient_get(pk=patient_id, clinic=clinic)
    q = request.GET.get("q", "").strip()
    qs = consultation_list_for_patient(patient=patient)
    if q:
        qs = qs.filter(
            DQ(diagnosis__icontains=q) |
            DQ(chief_complaints__icontains=q) |
            DQ(doctor__name__icontains=q)
        )
    total_count = qs.count()
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "patient/patient_consultations.html", {
        "patient": patient,
        "page_obj": page_obj,
        "total_count": total_count,
        "query": q,
    })


# ─── Consultations ────────────────────────────────────────────────────────────

@login_required
def new_consultation(request, patient_id):
    clinic = _get_clinic(request.user)
    patient = patient_get(pk=patient_id, clinic=clinic)
    if request.method == "POST":
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = consultation_create(
                patient=patient,
                doctor=patient.doctor,
                **form.cleaned_data,
            )
            logger.info("Consultation %s created for patient '%s' by %s", consultation.id, patient.name, request.user.username)
            messages.success(request, "Consultation saved.")
            if patient.doctor:
                return redirect("doctor_detail", pk=patient.doctor.id)
            return redirect("patient_consultations", patient_id=patient.id)
    else:
        form = ConsultationForm()
    return render(request, "patient/new_consultation.html", {"form": form, "patient": patient})


@login_required
def edit_consultation(request, patient_id, consultation_id):
    clinic = _get_clinic(request.user)
    patient = patient_get(pk=patient_id, clinic=clinic)
    consultation = get_object_or_404(Consultation, id=consultation_id, patient=patient)
    if request.method == "POST":
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            consultation_update(consultation=consultation, **form.cleaned_data)
            logger.info("Consultation %s updated by %s", consultation.id, request.user.username)
            messages.success(request, "Consultation updated.")
            return redirect("consultation_detail", consultation_id=consultation.id)
    else:
        form = ConsultationForm(instance=consultation)
    return render(request, "patient/edit_consultation.html", {
        "form": form, "patient": patient, "consultation": consultation,
    })


@login_required
def consultation_list_view(request):
    clinic = _get_clinic(request.user)
    query = request.GET.get("q", "").strip()
    qs = consultation_list(clinic=clinic, search=query)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "patient/consultation_list.html", {"page_obj": page_obj, "query": query})


@login_required
def consultation_detail(request, consultation_id):
    clinic = _get_clinic(request.user)
    consultation = get_object_or_404(
        Consultation.objects.select_related("patient", "doctor")
        .prefetch_related("lab_results__lab_test", "prescriptions__item"),
        id=consultation_id,
        patient__clinic=clinic,
    )
    return render(request, "patient/consultation_detail.html", {"consultation": consultation})


@login_required
def consultation_pdf(request, consultation_id):
    clinic = _get_clinic(request.user)
    consultation = get_object_or_404(
        Consultation.objects.select_related("patient", "doctor")
        .prefetch_related("lab_results__lab_test", "prescriptions__item"),
        id=consultation_id,
        patient__clinic=clinic,
    )
    html_string = render_to_string("patient/consultation_pdf.html", {
        "consultation": consultation,
        "request": request,
    })
    from weasyprint import HTML
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
    filename = f"consultation_{consultation.patient.name.replace(' ', '_')}_{consultation.id}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ─── Doctors ──────────────────────────────────────────────────────────────────

@login_required
def doctor_list_view(request):
    clinic = _get_clinic(request.user)
    doctors = doctor_list(clinic=clinic)
    return render(request, "patient/doctor_list.html", {"doctors": doctors})


@login_required
def doctor_detail(request, pk):
    clinic = _get_clinic(request.user)
    doctor = get_object_or_404(Doctor, pk=pk, clinic=clinic)
    queue = queue_list_active(clinic=clinic, doctor=doctor)
    lab_tests = LabTest.objects.filter(lab__clinic=clinic, is_active=True).select_related("lab")
    query = request.GET.get("q", "").strip()
    patients = (
        Patient.objects.filter(doctor=doctor, clinic=clinic, is_active=True)
        .order_by("name")
    )
    if query:
        patients = patients.filter(name__icontains=query)
    paginator = Paginator(patients, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "patient/doctor_detail.html", {
        "doctor": doctor,
        "queue": queue,
        "page_obj": page_obj,
        "query": query,
        "lab_tests": lab_tests,
    })


# ─── Queue management ─────────────────────────────────────────────────────────

@login_required
@require_POST
def add_to_queue(request, doctor_id, patient_id):
    clinic = _get_clinic(request.user)
    doctor = get_object_or_404(Doctor, id=doctor_id, clinic=clinic)
    patient = get_object_or_404(Patient, id=patient_id, clinic=clinic)

    if Queue.objects.filter(doctor=doctor, patient=patient, status="waiting").exists():
        logger.warning("Patient '%s' already queued for Dr. %s", patient.name, doctor.name)
        messages.warning(request, f"{patient.name} is already in Dr. {doctor.name}'s queue.")
        return redirect("patient_list")

    fee = Decimal("1300") if Bill.objects.filter(patient=patient).exists() else Decimal("1500")
    bill = Bill.objects.create(patient=patient, consultation=None, clinic=clinic, total_amount=fee)
    queue_add_patient(clinic=clinic, doctor=doctor, patient=patient)
    logger.info("Patient '%s' added to Dr. %s queue by %s, fee=%s", patient.name, doctor.name, request.user.username, fee)
    messages.success(request, f"{patient.name} added to Dr. {doctor.name}'s queue. Bill: KES {fee}")
    return redirect("patient_list")


@login_required
@require_POST
def add_to_queue_select(request, patient_id):
    clinic = _get_clinic(request.user)
    patient = get_object_or_404(Patient, id=patient_id, clinic=clinic)
    doctor_id = request.POST.get("doctor_id")
    doctor = get_object_or_404(Doctor, id=doctor_id, clinic=clinic)
    patient.doctor = doctor
    patient.save(update_fields=["doctor"])
    if Queue.objects.filter(doctor=doctor, patient=patient, status="waiting").exists():
        logger.warning("Patient '%s' already queued for Dr. %s (select)", patient.name, doctor.name)
        messages.warning(request, f"{patient.name} is already queued.")
    else:
        queue_add_patient(clinic=clinic, doctor=doctor, patient=patient)
        logger.info("Patient '%s' added to Dr. %s queue by %s", patient.name, doctor.name, request.user.username)
        messages.success(request, f"{patient.name} added to Dr. {doctor.name}'s queue.")
    return redirect("patient_list")


@login_required
@require_POST
def start_consultation(request, queue_id):
    clinic = _get_clinic(request.user)
    queue_item = get_object_or_404(Queue, id=queue_id, clinic=clinic)
    queue_item.start()
    return redirect("new_consultation", patient_id=queue_item.patient.id)


@login_required
@require_POST
def complete_consultation(request, queue_id):
    clinic = _get_clinic(request.user)
    queue_item = get_object_or_404(Queue, id=queue_id, clinic=clinic)
    queue_item.complete()
    consultation = queue_item.patient.consultations.first()
    if consultation and consultation.labor_charges:
        try:
            bill = Bill.objects.filter(patient=queue_item.patient, clinic=clinic, is_paid=False).latest("created_at")
            bill.total_amount += consultation.labor_charges
            bill.save(update_fields=["total_amount"])
            logger.info("Labor charges %s added to bill %s for patient '%s'", consultation.labor_charges, bill.id, queue_item.patient.name)
        except Bill.DoesNotExist:
            logger.warning("No unpaid bill found for patient '%s' (id=%s) to add labor charges", queue_item.patient.name, queue_item.patient.id)
    return redirect("doctor_detail", pk=queue_item.doctor.id)


# ─── AJAX / API ───────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def add_lab_test(request):
    name = request.POST.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Name is required."}, status=400)
    lab_test = LabTest.objects.create(name=name, description=request.POST.get("description", ""))
    return JsonResponse({"id": lab_test.id, "name": lab_test.name})


def patient_queue_count_api(request):
    clinic = _get_clinic(request.user)
    count = Queue.objects.filter(clinic=clinic, status__in=["in_progress", "waiting"]).count()
    return JsonResponse({"count": count})


def patient_complete_count_api(request):
    clinic = _get_clinic(request.user)
    count = Queue.objects.filter(
        clinic=clinic, status="completed",
        completed_at__date=timezone.now().date(),
    ).count()
    return JsonResponse({"count": count})


@login_required
def pipeline_notification(request):
    return render(request, "patient/pipeline_notification.html")
