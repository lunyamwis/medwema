from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from clinicmanager.models import Clinic
from emr.models import Lab, LabQueue, LabResult, LabTest
from emr.services import lab_queue_complete, lab_result_save, send_to_lab
from patient.models import Consultation, Doctor, Patient, Queue

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

class BaseEMRTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="emruser", password="pass123")
        cls.clinic = Clinic.objects.create(name="EMR Clinic", created_by=cls.user)
        cls.user.clinics.add(cls.clinic)
        cls.doctor = Doctor.objects.create(clinic=cls.clinic, name="Kildare")
        cls.lab = Lab.objects.create(
            clinic=cls.clinic,
            name="Main Lab",
            lab_type=Lab.LabType.INTERNAL,
        )
        cls.patient = Patient.objects.create(
            clinic=cls.clinic,
            name="Patient Zero",
            date_of_birth=datetime.date(1990, 1, 1),
            gender="M",
            phone_number="0700000100",
        )
        cls.consultation = Consultation.objects.create(patient=cls.patient)
        cls.lab_test = LabTest.objects.create(
            lab=cls.lab,
            name="Blood Glucose",
            unit="mmol/L",
            reference_min="3.9",
            reference_max="7.1",
            price=Decimal("500.00"),
            is_active=True,
        )


# ---------------------------------------------------------------------------
# LabTest model tests
# ---------------------------------------------------------------------------

class LabTestModelTests(BaseEMRTestCase):

    def test_reference_range_display_with_text(self):
        """reference_range_display() returns reference_text when it is set."""
        test = LabTest.objects.create(
            lab=self.lab,
            name="Urine Culture",
            reference_text="No growth",
        )
        self.assertEqual(test.reference_range_display(), "No growth")

    def test_reference_range_display_with_min_max(self):
        """reference_range_display() formats min–max with unit when reference_text is absent."""
        display = self.lab_test.reference_range_display()
        self.assertIn("3.9", display)
        self.assertIn("7.1", display)
        self.assertIn("mmol/L", display)

    def test_reference_range_display_no_info(self):
        """reference_range_display() returns 'N/A' when nothing is set."""
        test = LabTest.objects.create(lab=self.lab, name="Unknown Test")
        self.assertEqual(test.reference_range_display(), "N/A")

    def test_is_abnormal_numeric_high(self):
        """is_abnormal() returns True when result_value exceeds reference_max."""
        result = LabResult(
            lab_test=self.lab_test,
            consultation=self.consultation,
            result_value="10.5",  # > 7.1
        )
        self.assertTrue(result.is_abnormal())

    def test_is_abnormal_numeric_low(self):
        """is_abnormal() returns True when result_value is below reference_min."""
        result = LabResult(
            lab_test=self.lab_test,
            consultation=self.consultation,
            result_value="2.0",  # < 3.9
        )
        self.assertTrue(result.is_abnormal())

    def test_is_abnormal_normal_value(self):
        """is_abnormal() returns False when result_value is within range."""
        result = LabResult(
            lab_test=self.lab_test,
            consultation=self.consultation,
            result_value="5.0",  # within 3.9 – 7.1
        )
        self.assertFalse(result.is_abnormal())

    def test_is_abnormal_with_none_value(self):
        """is_abnormal() returns False gracefully when result_value is None."""
        result = LabResult(
            lab_test=self.lab_test,
            consultation=self.consultation,
            result_value=None,
        )
        self.assertFalse(result.is_abnormal())

    def test_is_abnormal_with_non_numeric_value(self):
        """is_abnormal() returns False for non-numeric (qualitative) results."""
        result = LabResult(
            lab_test=self.lab_test,
            consultation=self.consultation,
            result_value="Positive",
        )
        self.assertFalse(result.is_abnormal())


# ---------------------------------------------------------------------------
# LabQueue model tests
# ---------------------------------------------------------------------------

class LabQueueModelTests(BaseEMRTestCase):

    def _make_lab_queue(self):
        return LabQueue.objects.create(
            clinic=self.clinic,
            lab=self.lab,
            patient=self.patient,
            consultation=self.consultation,
            lab_test=self.lab_test,
        )

    def test_queue_number_auto_assigned(self):
        """queue_number is automatically assigned (>= 1) on first create."""
        lq = self._make_lab_queue()
        self.assertGreaterEqual(lq.queue_number, 1)

    def test_queue_number_increments(self):
        """Successive LabQueue entries for the same clinic/lab get incrementing numbers."""
        # Create a second lab_test so unique_together doesn't block us
        test2 = LabTest.objects.create(lab=self.lab, name="Haemoglobin", is_active=True)
        lq1 = self._make_lab_queue()
        lq2 = LabQueue.objects.create(
            clinic=self.clinic,
            lab=self.lab,
            patient=self.patient,
            consultation=self.consultation,
            lab_test=test2,
        )
        self.assertGreater(lq2.queue_number, lq1.queue_number)

    def test_start_updates_status(self):
        """start() changes status to 'in_progress' and sets started_at."""
        lq = self._make_lab_queue()
        self.assertIsNone(lq.started_at)
        before = timezone.now()
        lq.start()
        lq.refresh_from_db()
        self.assertEqual(lq.status, "in_progress")
        self.assertIsNotNone(lq.started_at)
        self.assertGreaterEqual(lq.started_at, before)

    def test_complete_updates_status(self):
        """complete() changes status to 'completed' and sets completed_at."""
        lq = self._make_lab_queue()
        lq.start()
        before = timezone.now()
        lq.complete()
        lq.refresh_from_db()
        self.assertEqual(lq.status, "completed")
        self.assertIsNotNone(lq.completed_at)
        self.assertGreaterEqual(lq.completed_at, before)


# ---------------------------------------------------------------------------
# EMRService tests
# ---------------------------------------------------------------------------

class SendToLabServiceTests(BaseEMRTestCase):

    def test_send_to_lab_creates_queue_items(self):
        """send_to_lab() creates one LabQueue item per requested test."""
        items = send_to_lab(
            clinic=self.clinic,
            patient=self.patient,
            consultation=self.consultation,
            lab_test_ids=[self.lab_test.pk],
        )
        self.assertEqual(len(items), 1)
        lq = items[0]
        self.assertEqual(lq.patient, self.patient)
        self.assertEqual(lq.lab_test, self.lab_test)
        self.assertEqual(lq.clinic, self.clinic)
        self.assertEqual(lq.status, "waiting")

    def test_send_to_lab_skips_non_existent_test(self):
        """send_to_lab() silently skips lab_test_ids that do not exist."""
        items = send_to_lab(
            clinic=self.clinic,
            patient=self.patient,
            consultation=self.consultation,
            lab_test_ids=[999999],
        )
        self.assertEqual(len(items), 0)

    def test_send_to_lab_skips_duplicates(self):
        """Calling send_to_lab() twice for the same test does not create a duplicate entry."""
        send_to_lab(
            clinic=self.clinic,
            patient=self.patient,
            consultation=self.consultation,
            lab_test_ids=[self.lab_test.pk],
        )
        second_call_items = send_to_lab(
            clinic=self.clinic,
            patient=self.patient,
            consultation=self.consultation,
            lab_test_ids=[self.lab_test.pk],
        )
        self.assertEqual(len(second_call_items), 0)
        total = LabQueue.objects.filter(
            clinic=self.clinic,
            patient=self.patient,
            lab_test=self.lab_test,
        ).count()
        self.assertEqual(total, 1)

    def test_send_to_lab_sets_doctor_queue_to_inlab(self):
        """send_to_lab() changes the doctor queue status to 'inlab' when provided."""
        doctor_queue = Queue.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient,
        )
        send_to_lab(
            clinic=self.clinic,
            patient=self.patient,
            consultation=self.consultation,
            lab_test_ids=[self.lab_test.pk],
            doctor_queue=doctor_queue,
        )
        doctor_queue.refresh_from_db()
        self.assertEqual(doctor_queue.status, "inlab")

    def test_send_to_lab_creates_bill_item(self):
        """send_to_lab() creates a billing item for each queued test."""
        from billing.models import BillItem
        send_to_lab(
            clinic=self.clinic,
            patient=self.patient,
            consultation=self.consultation,
            lab_test_ids=[self.lab_test.pk],
        )
        item = BillItem.objects.filter(
            bill__consultation=self.consultation,
            description__icontains="Blood Glucose",
        ).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.unit_price, self.lab_test.price)


class LabResultSaveServiceTests(BaseEMRTestCase):

    def test_lab_result_save_creates_result(self):
        """lab_result_save() creates a new LabResult for a consultation + test pair."""
        result = lab_result_save(
            consultation=self.consultation,
            lab_test=self.lab_test,
            result_value="5.6",
        )
        self.assertIsNotNone(result.pk)
        self.assertEqual(result.result_value, "5.6")
        self.assertEqual(result.consultation, self.consultation)
        self.assertEqual(result.lab_test, self.lab_test)

    def test_lab_result_save_creates_or_updates(self):
        """Calling lab_result_save() twice for the same pair updates rather than duplicating."""
        lab_result_save(
            consultation=self.consultation,
            lab_test=self.lab_test,
            result_value="5.6",
        )
        lab_result_save(
            consultation=self.consultation,
            lab_test=self.lab_test,
            result_value="6.2",
        )
        count = LabResult.objects.filter(
            consultation=self.consultation,
            lab_test=self.lab_test,
        ).count()
        self.assertEqual(count, 1)
        # And the stored value should be the latest one
        result = LabResult.objects.get(consultation=self.consultation, lab_test=self.lab_test)
        self.assertEqual(result.result_value, "6.2")

    def test_lab_result_save_uses_test_name_when_result_name_omitted(self):
        """result_name defaults to the LabTest name when not explicitly provided."""
        result = lab_result_save(
            consultation=self.consultation,
            lab_test=self.lab_test,
            result_value="4.5",
        )
        self.assertEqual(result.result_name, self.lab_test.name)


class LabQueueCompleteServiceTests(BaseEMRTestCase):

    def test_lab_queue_complete_updates_doctor_queue_to_from_lab(self):
        """lab_queue_complete() moves the doctor queue from 'inlab' to 'fromLab'
        when there are no remaining active lab items for the patient."""
        doctor_queue = Queue.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient,
            status="inlab",
        )
        lq = LabQueue.objects.create(
            clinic=self.clinic,
            lab=self.lab,
            patient=self.patient,
            consultation=self.consultation,
            lab_test=self.lab_test,
        )
        lq.start()
        lab_queue_complete(lab_queue=lq)
        doctor_queue.refresh_from_db()
        self.assertEqual(doctor_queue.status, "fromLab")

    def test_lab_queue_complete_does_not_update_doctor_queue_if_other_tests_pending(self):
        """Doctor queue stays 'inlab' when other lab items for the patient are still active."""
        test2 = LabTest.objects.create(lab=self.lab, name="Malaria RDT", is_active=True)
        doctor_queue = Queue.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient,
            status="inlab",
        )
        lq1 = LabQueue.objects.create(
            clinic=self.clinic,
            lab=self.lab,
            patient=self.patient,
            consultation=self.consultation,
            lab_test=self.lab_test,
        )
        # Second test is still waiting — patient is still in lab overall
        LabQueue.objects.create(
            clinic=self.clinic,
            lab=self.lab,
            patient=self.patient,
            consultation=self.consultation,
            lab_test=test2,
        )
        lq1.start()
        lab_queue_complete(lab_queue=lq1)
        doctor_queue.refresh_from_db()
        self.assertEqual(doctor_queue.status, "inlab")

    def test_lab_queue_complete_marks_queue_completed(self):
        """lab_queue_complete() marks the LabQueue itself as 'completed'."""
        lq = LabQueue.objects.create(
            clinic=self.clinic,
            lab=self.lab,
            patient=self.patient,
            consultation=self.consultation,
            lab_test=self.lab_test,
        )
        lq.start()
        lab_queue_complete(lab_queue=lq)
        lq.refresh_from_db()
        self.assertEqual(lq.status, "completed")
