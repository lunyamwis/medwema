from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from clinicmanager.models import Clinic
from patient.models import Consultation, Doctor, Patient, Queue


def patient_create(
    *,
    clinic: Clinic,
    name: str,
    date_of_birth,
    gender: str,
    phone_number: str,
    email: str = "",
    address: str = "",
    blood_group: str = "unknown",
    emergency_contact_name: str = "",
    emergency_contact_phone: str = "",
    doctor: Optional[Doctor] = None,
) -> Patient:
    patient = Patient(
        clinic=clinic,
        name=name,
        date_of_birth=date_of_birth,
        gender=gender,
        phone_number=phone_number,
        email=email or None,
        address=address or None,
        blood_group=blood_group,
        emergency_contact_name=emergency_contact_name or None,
        emergency_contact_phone=emergency_contact_phone or None,
        doctor=doctor,
    )
    patient.full_clean()
    patient.save()
    return patient


def patient_update(*, patient: Patient, **fields) -> Patient:
    for attr, value in fields.items():
        setattr(patient, attr, value)
    patient.full_clean()
    patient.save()
    return patient


def consultation_create(*, patient: Patient, doctor: Optional[Doctor] = None, **fields) -> Consultation:
    consultation = Consultation(patient=patient, doctor=doctor, **fields)
    consultation.full_clean()
    consultation.save()
    return consultation


def consultation_update(*, consultation: Consultation, **fields) -> Consultation:
    for attr, value in fields.items():
        setattr(consultation, attr, value)
    consultation.full_clean()
    consultation.save()
    return consultation


@transaction.atomic
def queue_add_patient(
    *,
    clinic: Clinic,
    doctor: Doctor,
    patient: Patient,
    priority: str = "normal",
) -> Queue:
    queue = Queue(
        clinic=clinic,
        doctor=doctor,
        patient=patient,
        priority=priority,
    )
    queue.save()
    return queue


def queue_start(*, queue: Queue) -> Queue:
    queue.start()
    return queue


def queue_complete(*, queue: Queue, consultation: Optional[Consultation] = None) -> Queue:
    queue.complete()
    if consultation and consultation.labor_charges:
        from billing.services import bill_add_item, bill_get_or_create
        bill = bill_get_or_create(patient=queue.patient, clinic=queue.clinic, consultation=consultation)
        if consultation.labor_charges > 0:
            bill_add_item(
                bill=bill,
                description="Consultation Fee",
                quantity=1,
                unit_price=consultation.labor_charges,
            )
    return queue
