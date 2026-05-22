from __future__ import annotations

from django.db import transaction

from billing.services import bill_add_item, bill_get_or_create
from clinicmanager.models import Clinic
from emr.models import Lab, LabQueue, LabResult, LabTest
from patient.models import Consultation, Patient, Queue


@transaction.atomic
def send_to_lab(
    *,
    clinic: Clinic,
    patient: Patient,
    consultation: Consultation,
    lab_test_ids: list[int],
    doctor_queue: Queue | None = None,
) -> list[LabQueue]:
    lab = Lab.objects.filter(clinic=clinic, lab_type="Internal").first()
    queue_items = []

    for test_id in lab_test_ids:
        try:
            lab_test = LabTest.objects.get(pk=test_id, is_active=True)
        except LabTest.DoesNotExist:
            continue

        already_queued = LabQueue.objects.filter(
            clinic=clinic,
            patient=patient,
            lab_test=lab_test,
            status__in=["waiting", "in_progress"],
        ).exists()
        if already_queued:
            continue

        lq = LabQueue.objects.create(
            clinic=clinic,
            lab=lab,
            patient=patient,
            consultation=consultation,
            lab_test=lab_test,
        )
        queue_items.append(lq)

        bill = bill_get_or_create(patient=patient, clinic=clinic, consultation=consultation)
        bill_add_item(
            bill=bill,
            description=f"Lab: {lab_test.name}",
            quantity=1,
            unit_price=lab_test.price,
        )

    if doctor_queue:
        doctor_queue.status = "inlab"
        doctor_queue.save(update_fields=["status"])

    return queue_items


def lab_result_save(
    *,
    consultation: Consultation,
    lab_test: LabTest,
    result_value: str,
    result_name: str = "",
) -> LabResult:
    result, _ = LabResult.objects.update_or_create(
        consultation=consultation,
        lab_test=lab_test,
        defaults={
            "result_value": result_value,
            "result_name": result_name or lab_test.name,
        },
    )
    return result


def lab_queue_start(*, lab_queue: LabQueue) -> LabQueue:
    lab_queue.start()
    return lab_queue


def lab_queue_complete(*, lab_queue: LabQueue) -> LabQueue:
    lab_queue.complete()
    clinic_queue = Queue.objects.filter(
        clinic=lab_queue.clinic,
        patient=lab_queue.patient,
        status="inlab",
    ).first()
    if clinic_queue:
        still_in_lab = LabQueue.objects.filter(
            clinic=lab_queue.clinic,
            patient=lab_queue.patient,
            status__in=["waiting", "in_progress"],
        ).exclude(pk=lab_queue.pk).exists()
        if not still_in_lab:
            clinic_queue.status = "fromLab"
            clinic_queue.save(update_fields=["status"])
    return lab_queue
