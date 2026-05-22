from __future__ import annotations

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from clinicmanager.models import Clinic
from patient.models import Consultation, Doctor, Patient, Queue
from patient.selectors import patient_list, queue_waiting_count
from patient.services import consultation_create, patient_create, queue_add_patient

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared base fixtures
# ---------------------------------------------------------------------------

class BasePatientTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="pass123")
        cls.clinic = Clinic.objects.create(name="Test Clinic", created_by=cls.user)
        cls.user.clinics.add(cls.clinic)
        cls.doctor = Doctor.objects.create(
            clinic=cls.clinic,
            name="House",
            specialization="General",
        )

    def _make_patient(self, name="Alice Wambui", phone="0700000001"):
        return Patient.objects.create(
            clinic=self.clinic,
            name=name,
            date_of_birth=datetime.date(1990, 6, 15),
            gender="F",
            phone_number=phone,
        )


# ---------------------------------------------------------------------------
# PatientModel tests
# ---------------------------------------------------------------------------

class PatientModelTests(BasePatientTestCase):

    def test_patient_number_auto_generated(self):
        """Patient number is generated on save and begins with 'P'."""
        patient = self._make_patient()
        self.assertIsNotNone(patient.patient_number)
        self.assertTrue(
            patient.patient_number.startswith("P"),
            f"Expected patient_number to start with 'P', got: {patient.patient_number}",
        )

    def test_patient_number_includes_clinic_id(self):
        """Patient number embeds the clinic ID (format P{clinic_id:03d}{seq:05d})."""
        patient = self._make_patient(phone="0700009001")
        expected_prefix = f"P{self.clinic.id:03d}"
        self.assertTrue(patient.patient_number.startswith(expected_prefix))

    def test_patient_age_calculation(self):
        """age() returns the correct integer age based on date_of_birth."""
        today = timezone.now().date()
        dob = today.replace(year=today.year - 30)
        patient = Patient.objects.create(
            clinic=self.clinic,
            name="Bob Kamau",
            date_of_birth=dob,
            gender="M",
            phone_number="0700000002",
        )
        self.assertEqual(patient.age(), 30)

    def test_patient_age_before_birthday_this_year(self):
        """age() is one less when the birthday has not yet occurred this year."""
        today = timezone.now().date()
        # Birthday is tomorrow — patient has not turned 30 yet
        birthday_tomorrow = today + datetime.timedelta(days=1)
        dob = birthday_tomorrow.replace(year=today.year - 30)
        patient = Patient.objects.create(
            clinic=self.clinic,
            name="Clara Njeri",
            date_of_birth=dob,
            gender="F",
            phone_number="0700000003",
        )
        self.assertEqual(patient.age(), 29)

    def test_patient_str(self):
        """__str__ returns the patient's full name."""
        patient = self._make_patient(name="Diana Otieno", phone="0700009999")
        self.assertEqual(str(patient), "Diana Otieno")


# ---------------------------------------------------------------------------
# ConsultationModel tests
# ---------------------------------------------------------------------------

class ConsultationModelTests(BasePatientTestCase):

    def setUp(self):
        self.patient = self._make_patient(phone="0700001100")

    def test_consultation_number_auto_generated(self):
        """consultation_number is set on save and starts with 'C'."""
        consultation = Consultation.objects.create(patient=self.patient)
        self.assertIsNotNone(consultation.consultation_number)
        self.assertTrue(
            consultation.consultation_number.startswith("C"),
            f"Expected to start with 'C', got: {consultation.consultation_number}",
        )

    def test_consultation_str_contains_patient_name(self):
        """__str__ mentions the patient's name."""
        consultation = Consultation.objects.create(patient=self.patient)
        self.assertIn(self.patient.name, str(consultation))

    def test_consultation_default_status_is_active(self):
        """A freshly created consultation defaults to 'active' status."""
        consultation = Consultation.objects.create(patient=self.patient)
        self.assertEqual(consultation.status, "active")

    def test_consultation_numbers_are_unique_within_same_day(self):
        """Two consultations created on the same day get different numbers."""
        c1 = Consultation.objects.create(patient=self.patient)
        c2 = Consultation.objects.create(patient=self.patient)
        self.assertNotEqual(c1.consultation_number, c2.consultation_number)


# ---------------------------------------------------------------------------
# QueueModel tests
# ---------------------------------------------------------------------------

class QueueModelTests(BasePatientTestCase):

    def setUp(self):
        self.patient = self._make_patient(phone="0700001200")

    def _make_queue(self):
        return Queue.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient,
        )

    def test_queue_default_status_is_waiting(self):
        """A new queue entry defaults to 'waiting'."""
        queue = self._make_queue()
        self.assertEqual(queue.status, "waiting")

    def test_queue_start(self):
        """start() sets status to 'in_progress' and records started_at."""
        queue = self._make_queue()
        self.assertIsNone(queue.started_at)
        before = timezone.now()
        queue.start()
        queue.refresh_from_db()
        self.assertEqual(queue.status, "in_progress")
        self.assertIsNotNone(queue.started_at)
        self.assertGreaterEqual(queue.started_at, before)

    def test_queue_complete(self):
        """complete() sets status to 'completed' and records completed_at."""
        queue = self._make_queue()
        queue.start()
        before = timezone.now()
        queue.complete()
        queue.refresh_from_db()
        self.assertEqual(queue.status, "completed")
        self.assertIsNotNone(queue.completed_at)
        self.assertGreaterEqual(queue.completed_at, before)

    def test_queue_number_auto_assigned_sequentially(self):
        """queue_number increments for each new entry under the same doctor/clinic."""
        q1 = self._make_queue()
        q2 = Queue.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient=self.patient,
        )
        self.assertGreaterEqual(q1.queue_number, 1)
        self.assertGreater(q2.queue_number, q1.queue_number)


# ---------------------------------------------------------------------------
# PatientService tests
# ---------------------------------------------------------------------------

class PatientServiceTests(BasePatientTestCase):

    def test_patient_create(self):
        """patient_create() persists a patient with the supplied fields."""
        patient = patient_create(
            clinic=self.clinic,
            name="Eve Njoroge",
            date_of_birth=datetime.date(1985, 3, 20),
            gender="F",
            phone_number="0711111111",
            email="eve@example.com",
            blood_group="O+",
        )
        self.assertIsNotNone(patient.pk)
        self.assertEqual(patient.name, "Eve Njoroge")
        self.assertEqual(patient.clinic, self.clinic)
        self.assertEqual(patient.blood_group, "O+")
        # Confirm presence in the database
        db_patient = Patient.objects.get(pk=patient.pk)
        self.assertEqual(db_patient.name, "Eve Njoroge")

    def test_patient_create_sets_patient_number(self):
        """patient_create() triggers patient_number auto-generation."""
        patient = patient_create(
            clinic=self.clinic,
            name="Frank Mwangi",
            date_of_birth=datetime.date(1992, 7, 4),
            gender="M",
            phone_number="0722222222",
        )
        self.assertIsNotNone(patient.patient_number)
        self.assertTrue(patient.patient_number.startswith("P"))

    def test_consultation_create(self):
        """consultation_create() saves a consultation linked to the correct patient."""
        patient = self._make_patient(name="Grace Achieng", phone="0733333333")
        consultation = consultation_create(
            patient=patient,
            doctor=self.doctor,
            chief_complaints="Fever and headache",
        )
        self.assertIsNotNone(consultation.pk)
        self.assertEqual(consultation.patient, patient)
        self.assertEqual(consultation.doctor, self.doctor)
        self.assertEqual(consultation.chief_complaints, "Fever and headache")
        self.assertIsNotNone(consultation.consultation_number)

    def test_consultation_create_without_doctor(self):
        """consultation_create() works when no doctor is provided."""
        patient = self._make_patient(name="Harriet Muthoni", phone="0734444444")
        consultation = consultation_create(patient=patient)
        self.assertIsNotNone(consultation.pk)
        self.assertIsNone(consultation.doctor)

    def test_queue_add_patient(self):
        """queue_add_patient() creates a Queue item with status 'waiting'."""
        patient = self._make_patient(name="Henry Kimani", phone="0744444444")
        queue = queue_add_patient(
            clinic=self.clinic,
            doctor=self.doctor,
            patient=patient,
        )
        self.assertIsNotNone(queue.pk)
        self.assertEqual(queue.status, "waiting")
        self.assertEqual(queue.patient, patient)
        self.assertEqual(queue.clinic, self.clinic)
        self.assertEqual(queue.doctor, self.doctor)

    def test_queue_add_patient_custom_priority(self):
        """queue_add_patient() honours the priority argument."""
        patient = self._make_patient(name="Iris Wanjiku", phone="0755555555")
        queue = queue_add_patient(
            clinic=self.clinic,
            doctor=self.doctor,
            patient=patient,
            priority="urgent",
        )
        self.assertEqual(queue.priority, "urgent")


# ---------------------------------------------------------------------------
# PatientSelector tests
# ---------------------------------------------------------------------------

class PatientSelectorTests(BasePatientTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.patient_alice = Patient.objects.create(
            clinic=cls.clinic,
            name="Alice Wambui",
            date_of_birth=datetime.date(1990, 1, 1),
            gender="F",
            phone_number="0700000010",
        )
        cls.patient_bob = Patient.objects.create(
            clinic=cls.clinic,
            name="Bob Kariuki",
            date_of_birth=datetime.date(1985, 5, 5),
            gender="M",
            phone_number="0700000011",
        )
        cls.patient_carol = Patient.objects.create(
            clinic=cls.clinic,
            name="Carol Wangari",
            date_of_birth=datetime.date(1978, 9, 9),
            gender="F",
            phone_number="0700000012",
        )

    def test_patient_list_search_by_name(self):
        """Searching by name returns only matching patients."""
        results = patient_list(clinic=self.clinic, search="Alice")
        names = list(results.values_list("name", flat=True))
        self.assertIn("Alice Wambui", names)
        self.assertNotIn("Bob Kariuki", names)
        self.assertNotIn("Carol Wangari", names)

    def test_patient_list_search_is_case_insensitive(self):
        """Name search is case-insensitive."""
        results = patient_list(clinic=self.clinic, search="carol")
        names = list(results.values_list("name", flat=True))
        self.assertIn("Carol Wangari", names)

    def test_patient_list_no_search_returns_all_active(self):
        """With no search term all active patients in the clinic are returned."""
        results = patient_list(clinic=self.clinic, search="")
        self.assertGreaterEqual(results.count(), 3)

    def test_patient_list_search_by_phone(self):
        """Searching by phone number fragment returns the matching patient."""
        results = patient_list(clinic=self.clinic, search="0700000011")
        names = list(results.values_list("name", flat=True))
        self.assertIn("Bob Kariuki", names)

    def test_patient_list_inactive_excluded_by_default(self):
        """Inactive patients are excluded when active_only=True (the default)."""
        inactive = Patient.objects.create(
            clinic=self.clinic,
            name="Zephyr Inactive",
            date_of_birth=datetime.date(1980, 1, 1),
            gender="M",
            phone_number="0799999999",
            is_active=False,
        )
        results = patient_list(clinic=self.clinic)
        pks = list(results.values_list("pk", flat=True))
        self.assertNotIn(inactive.pk, pks)

    def test_queue_waiting_count(self):
        """queue_waiting_count() counts waiting and in-progress entries for the clinic."""
        # Capture the baseline so other tests' teardown doesn't interfere
        baseline = queue_waiting_count(clinic=self.clinic)
        patients_created = []
        for i, phone in enumerate(["0800000001", "0800000002"], start=1):
            p = Patient.objects.create(
                clinic=self.clinic,
                name=f"WaitPatient {i}",
                date_of_birth=datetime.date(1995, 1, 1),
                gender="M",
                phone_number=phone,
            )
            patients_created.append(p)
            Queue.objects.create(
                clinic=self.clinic,
                doctor=self.doctor,
                patient=p,
            )
        count = queue_waiting_count(clinic=self.clinic)
        self.assertEqual(count, baseline + 2)

    def test_queue_waiting_count_excludes_completed(self):
        """Completed queue entries are not included in the waiting count."""
        patient = Patient.objects.create(
            clinic=self.clinic,
            name="Done Patient",
            date_of_birth=datetime.date(1993, 3, 3),
            gender="F",
            phone_number="0800000099",
        )
        queue = Queue.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient=patient,
        )
        count_before = queue_waiting_count(clinic=self.clinic)
        queue.complete()
        count_after = queue_waiting_count(clinic=self.clinic)
        self.assertEqual(count_after, count_before - 1)


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------

class PatientViewTests(BasePatientTestCase):

    def setUp(self):
        self.client = Client()

    def test_patient_list_requires_login(self):
        """Unauthenticated GET /patients/ redirects to login (302)."""
        response = self.client.get(reverse("patient_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"].lower())

    def test_patient_list_authenticated(self):
        """Authenticated GET /patients/ returns 200."""
        self.client.login(username="testuser", password="pass123")
        response = self.client.get(reverse("patient_list"))
        self.assertEqual(response.status_code, 200)

    def test_register_patient_get_requires_login(self):
        """Unauthenticated GET /patients/register/ redirects to login."""
        response = self.client.get(reverse("register_patient"))
        self.assertEqual(response.status_code, 302)

    def test_register_patient_get_authenticated(self):
        """Authenticated GET /patients/register/ returns the registration form (200)."""
        self.client.login(username="testuser", password="pass123")
        response = self.client.get(reverse("register_patient"))
        self.assertEqual(response.status_code, 200)

    def test_register_patient_post_creates_patient_and_redirects(self):
        """Valid POST creates a patient and redirects to the detail page."""
        self.client.login(username="testuser", password="pass123")
        initial_count = Patient.objects.filter(clinic=self.clinic).count()
        data = {
            "name": "James Ochieng",
            "date_of_birth": "1991-04-10",
            "gender": "M",
            "phone_number": "0766666666",
            "blood_group": "B+",
            "email": "",
            "address": "",
            "emergency_contact_name": "",
            "emergency_contact_phone": "",
        }
        response = self.client.post(reverse("register_patient"), data)
        # Should redirect to patient_detail
        self.assertEqual(response.status_code, 302)
        new_count = Patient.objects.filter(clinic=self.clinic).count()
        self.assertEqual(new_count, initial_count + 1)
        created = Patient.objects.filter(clinic=self.clinic, name="James Ochieng").first()
        self.assertIsNotNone(created)
        self.assertIsNotNone(created.patient_number)

    def test_register_patient_post_invalid_returns_form(self):
        """POST with missing required fields re-renders the form without creating a patient."""
        self.client.login(username="testuser", password="pass123")
        initial_count = Patient.objects.filter(clinic=self.clinic).count()
        # name and date_of_birth are required; send empty form
        response = self.client.post(reverse("register_patient"), {"name": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Patient.objects.filter(clinic=self.clinic).count(), initial_count)
