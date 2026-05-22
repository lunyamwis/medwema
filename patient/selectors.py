from __future__ import annotations

from django.db.models import Q, QuerySet

from clinicmanager.models import Clinic
from patient.models import Consultation, Doctor, Patient, Queue


def patient_list(*, clinic: Clinic, search: str = "", active_only: bool = True) -> QuerySet:
    qs = (
        Patient.objects.filter(clinic=clinic)
        .select_related("doctor", "clinic")
        .order_by("name")
    )
    if active_only:
        qs = qs.filter(is_active=True)
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(patient_number__icontains=search)
        )
    return qs


def patient_get(*, pk: int, clinic: Clinic) -> Patient:
    return Patient.objects.select_related("doctor", "clinic").get(pk=pk, clinic=clinic)


def doctor_list(*, clinic: Clinic) -> QuerySet:
    return Doctor.objects.filter(clinic=clinic).select_related("user").order_by("name")


def doctor_get(*, pk: int) -> Doctor:
    return Doctor.objects.select_related("clinic", "user").get(pk=pk)


def consultation_list(*, clinic: Clinic, search: str = "") -> QuerySet:
    qs = (
        Consultation.objects.filter(patient__clinic=clinic)
        .select_related("patient", "doctor")
        .order_by("-date")
    )
    if search:
        qs = qs.filter(Q(patient__name__icontains=search) | Q(diagnosis__icontains=search))
    return qs


def consultation_get(*, pk: int) -> Consultation:
    return Consultation.objects.select_related("patient", "doctor", "patient__clinic").get(pk=pk)


def consultation_list_for_patient(*, patient: Patient) -> QuerySet:
    return (
        Consultation.objects.filter(patient=patient)
        .select_related("doctor")
        .prefetch_related("lab_results__lab_test", "prescriptions__item")
        .order_by("-date")
    )


def queue_list_active(*, clinic: Clinic, doctor: Doctor) -> QuerySet:
    return (
        Queue.objects.filter(clinic=clinic, doctor=doctor)
        .exclude(status__in=["completed", "skipped"])
        .select_related("patient", "doctor")
        .order_by("priority", "created_at")
    )


def queue_list_completed_today(*, clinic: Clinic) -> QuerySet:
    from django.utils import timezone
    today = timezone.now().date()
    return Queue.objects.filter(
        clinic=clinic,
        status="completed",
        completed_at__date=today,
    ).select_related("patient", "doctor")


def queue_waiting_count(*, clinic: Clinic) -> int:
    return Queue.objects.filter(clinic=clinic, status__in=["waiting", "in_progress"]).count()


def queue_completed_count(*, clinic: Clinic) -> int:
    from django.utils import timezone
    today = timezone.now().date()
    return Queue.objects.filter(clinic=clinic, status="completed", completed_at__date=today).count()
