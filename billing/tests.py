from __future__ import annotations

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from billing.models import Bill, BillItem, Payment
from billing.services import bill_add_item, bill_get_or_create, payment_mark_manual
from clinicmanager.models import Clinic
from patient.models import Consultation, Doctor, Patient

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

class BaseBillingTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="billinguser", password="pass123")
        cls.clinic = Clinic.objects.create(name="Billing Clinic", created_by=cls.user)
        cls.user.clinics.add(cls.clinic)
        cls.doctor = Doctor.objects.create(clinic=cls.clinic, name="Grey")
        cls.patient = Patient.objects.create(
            clinic=cls.clinic,
            name="Bill Patient",
            date_of_birth=datetime.date(1985, 4, 1),
            gender="F",
            phone_number="0700000200",
        )
        cls.consultation = Consultation.objects.create(patient=cls.patient)

    def _make_bill(self, total=Decimal("1000.00"), discount=Decimal("0.00")):
        return Bill.objects.create(
            patient=self.patient,
            clinic=self.clinic,
            consultation=self.consultation,
            total_amount=total,
            discount=discount,
        )


# ---------------------------------------------------------------------------
# Bill model tests
# ---------------------------------------------------------------------------

class BillModelTests(BaseBillingTestCase):

    def test_net_amount_without_discount(self):
        """net_amount returns total_amount when discount is zero."""
        bill = self._make_bill(total=Decimal("1500.00"), discount=Decimal("0.00"))
        self.assertEqual(bill.net_amount, Decimal("1500.00"))

    def test_net_amount_with_discount(self):
        """net_amount deducts the discount from total_amount."""
        bill = self._make_bill(total=Decimal("2000.00"), discount=Decimal("300.00"))
        self.assertEqual(bill.net_amount, Decimal("1700.00"))

    def test_net_amount_discount_cannot_go_below_zero(self):
        """net_amount is floored at 0.00 when discount exceeds total."""
        bill = self._make_bill(total=Decimal("100.00"), discount=Decimal("200.00"))
        self.assertEqual(bill.net_amount, Decimal("0.00"))

    def test_status_property_unpaid(self):
        """status returns 'Unpaid' for a bill that has not been paid."""
        bill = self._make_bill()
        self.assertEqual(bill.status, "Unpaid")

    def test_status_property_paid(self):
        """status returns 'Paid' once is_paid is set to True."""
        bill = self._make_bill()
        bill.is_paid = True
        bill.save(update_fields=["is_paid"])
        self.assertEqual(bill.status, "Paid")


# ---------------------------------------------------------------------------
# BillItem model tests
# ---------------------------------------------------------------------------

class BillItemModelTests(BaseBillingTestCase):

    def test_item_total_computed_on_save(self):
        """BillItem.total is automatically computed as quantity × unit_price on save."""
        bill = self._make_bill()
        item = BillItem.objects.create(
            bill=bill,
            description="Consultation Fee",
            quantity=3,
            unit_price=Decimal("250.00"),
        )
        self.assertEqual(item.total, Decimal("750.00"))

    def test_item_total_updates_on_edit(self):
        """Changing quantity and re-saving recalculates total correctly."""
        bill = self._make_bill()
        item = BillItem.objects.create(
            bill=bill,
            description="Lab Test",
            quantity=1,
            unit_price=Decimal("400.00"),
        )
        item.quantity = 2
        item.save()
        self.assertEqual(item.total, Decimal("800.00"))

    def test_item_str(self):
        """BillItem __str__ includes the description and quantity."""
        bill = self._make_bill()
        item = BillItem.objects.create(
            bill=bill,
            description="Paracetamol",
            quantity=10,
            unit_price=Decimal("5.00"),
        )
        self.assertIn("Paracetamol", str(item))
        self.assertIn("10", str(item))


# ---------------------------------------------------------------------------
# Payment model tests
# ---------------------------------------------------------------------------

class PaymentModelTests(BaseBillingTestCase):

    def test_receipt_number_auto_generated(self):
        """receipt_number is set on save and starts with 'RCP'."""
        bill = self._make_bill()
        payment = Payment.objects.create(
            bill=bill,
            reference="TEST-REF-001",
            amount=Decimal("500.00"),
        )
        self.assertIsNotNone(payment.receipt_number)
        self.assertTrue(
            payment.receipt_number.startswith("RCP"),
            f"Expected receipt_number to start with 'RCP', got: {payment.receipt_number}",
        )

    def test_mark_as_paid_manual(self):
        """mark_as_paid(manual=True) sets status to 'manual', records paid_at, and marks bill paid."""
        bill = self._make_bill()
        payment = Payment.objects.create(
            bill=bill,
            reference="MANUAL-001",
            amount=Decimal("1000.00"),
        )
        before = timezone.now()
        payment.mark_as_paid(manual=True)
        payment.refresh_from_db()
        bill.refresh_from_db()
        self.assertEqual(payment.status, "manual")
        self.assertIsNotNone(payment.paid_at)
        self.assertGreaterEqual(payment.paid_at, before)
        self.assertTrue(bill.is_paid)

    def test_mark_as_paid_online(self):
        """mark_as_paid(manual=False) sets status to 'success' and marks bill paid."""
        bill = self._make_bill()
        payment = Payment.objects.create(
            bill=bill,
            reference="PAYSTACK-002",
            amount=Decimal("1000.00"),
        )
        payment.mark_as_paid(manual=False)
        payment.refresh_from_db()
        bill.refresh_from_db()
        self.assertEqual(payment.status, "success")
        self.assertTrue(bill.is_paid)


# ---------------------------------------------------------------------------
# BillingService tests
# ---------------------------------------------------------------------------

class BillGetOrCreateServiceTests(BaseBillingTestCase):

    def test_bill_get_or_create_creates_bill(self):
        """bill_get_or_create() creates a bill for a consultation that has none yet."""
        # Use a fresh consultation with no existing bill
        fresh_patient = Patient.objects.create(
            clinic=self.clinic,
            name="Fresh Patient",
            date_of_birth=datetime.date(1992, 2, 2),
            gender="M",
            phone_number="0700000201",
        )
        fresh_consultation = Consultation.objects.create(patient=fresh_patient)
        bill = bill_get_or_create(
            patient=fresh_patient,
            clinic=self.clinic,
            consultation=fresh_consultation,
        )
        self.assertIsNotNone(bill.pk)
        self.assertEqual(bill.patient, fresh_patient)

    def test_bill_get_or_create_idempotent(self):
        """Calling bill_get_or_create() twice for the same consultation returns the same bill."""
        fresh_patient = Patient.objects.create(
            clinic=self.clinic,
            name="Idempotent Patient",
            date_of_birth=datetime.date(1988, 8, 8),
            gender="F",
            phone_number="0700000202",
        )
        fresh_consultation = Consultation.objects.create(patient=fresh_patient)
        bill_first = bill_get_or_create(
            patient=fresh_patient,
            clinic=self.clinic,
            consultation=fresh_consultation,
        )
        bill_second = bill_get_or_create(
            patient=fresh_patient,
            clinic=self.clinic,
            consultation=fresh_consultation,
        )
        self.assertEqual(bill_first.pk, bill_second.pk)
        self.assertEqual(
            Bill.objects.filter(consultation=fresh_consultation).count(),
            1,
        )

    def test_bill_get_or_create_without_consultation(self):
        """bill_get_or_create() without a consultation always creates a new standalone bill."""
        b1 = bill_get_or_create(patient=self.patient, clinic=self.clinic, consultation=None)
        b2 = bill_get_or_create(patient=self.patient, clinic=self.clinic, consultation=None)
        # Each call without consultation creates a new bill
        self.assertNotEqual(b1.pk, b2.pk)


class BillAddItemServiceTests(BaseBillingTestCase):

    def test_bill_add_item_creates_bill_item(self):
        """bill_add_item() creates a BillItem linked to the bill."""
        bill = bill_get_or_create(
            patient=self.patient,
            clinic=self.clinic,
            consultation=self.consultation,
        )
        item = bill_add_item(
            bill=bill,
            description="X-Ray",
            quantity=1,
            unit_price=Decimal("1200.00"),
        )
        self.assertIsNotNone(item.pk)
        self.assertEqual(item.description, "X-Ray")
        self.assertEqual(item.total, Decimal("1200.00"))

    def test_bill_add_item_updates_total(self):
        """After bill_add_item() the bill's total_amount reflects the sum of all items."""
        fresh_patient = Patient.objects.create(
            clinic=self.clinic,
            name="Total Patient",
            date_of_birth=datetime.date(1996, 6, 6),
            gender="M",
            phone_number="0700000203",
        )
        fresh_consultation = Consultation.objects.create(patient=fresh_patient)
        bill = bill_get_or_create(
            patient=fresh_patient,
            clinic=self.clinic,
            consultation=fresh_consultation,
        )
        bill_add_item(bill=bill, description="Lab Test", quantity=1, unit_price=Decimal("500.00"))
        bill_add_item(bill=bill, description="Consultation", quantity=1, unit_price=Decimal("300.00"))
        bill.refresh_from_db()
        self.assertEqual(bill.total_amount, Decimal("800.00"))

    def test_bill_add_item_multiple_quantity(self):
        """bill_add_item() computes total correctly for quantity > 1."""
        fresh_patient = Patient.objects.create(
            clinic=self.clinic,
            name="Multi-Qty Patient",
            date_of_birth=datetime.date(1994, 4, 4),
            gender="F",
            phone_number="0700000204",
        )
        fresh_consultation = Consultation.objects.create(patient=fresh_patient)
        bill = bill_get_or_create(
            patient=fresh_patient,
            clinic=self.clinic,
            consultation=fresh_consultation,
        )
        item = bill_add_item(
            bill=bill,
            description="Paracetamol 500mg",
            quantity=5,
            unit_price=Decimal("20.00"),
        )
        self.assertEqual(item.total, Decimal("100.00"))
        bill.refresh_from_db()
        self.assertEqual(bill.total_amount, Decimal("100.00"))


class PaymentMarkManualServiceTests(BaseBillingTestCase):

    def test_payment_mark_manual_marks_bill_paid(self):
        """payment_mark_manual() marks the associated bill as paid."""
        fresh_patient = Patient.objects.create(
            clinic=self.clinic,
            name="Cash Patient",
            date_of_birth=datetime.date(1983, 3, 30),
            gender="M",
            phone_number="0700000205",
        )
        fresh_consultation = Consultation.objects.create(patient=fresh_patient)
        bill = bill_get_or_create(
            patient=fresh_patient,
            clinic=self.clinic,
            consultation=fresh_consultation,
        )
        bill_add_item(bill=bill, description="Consultation", quantity=1, unit_price=Decimal("800.00"))
        bill.refresh_from_db()

        payment = payment_mark_manual(
            bill=bill,
            amount=bill.net_amount,
            created_by=self.user,
            payment_method="CASH",
        )
        bill.refresh_from_db()
        self.assertTrue(bill.is_paid)
        self.assertEqual(payment.status, "manual")
        self.assertEqual(payment.payment_method, "CASH")
        self.assertEqual(payment.created_by, self.user)

    def test_payment_mark_manual_generates_unique_reference(self):
        """payment_mark_manual() creates a payment with a non-empty unique reference."""
        fresh_patient = Patient.objects.create(
            clinic=self.clinic,
            name="Ref Patient",
            date_of_birth=datetime.date(1991, 11, 11),
            gender="F",
            phone_number="0700000206",
        )
        fresh_consultation = Consultation.objects.create(patient=fresh_patient)
        bill = bill_get_or_create(
            patient=fresh_patient,
            clinic=self.clinic,
            consultation=fresh_consultation,
        )
        p1 = payment_mark_manual(
            bill=bill,
            amount=Decimal("100.00"),
            created_by=self.user,
        )
        # Create a second bill so we can test again
        bill2 = bill_get_or_create(patient=fresh_patient, clinic=self.clinic, consultation=None)
        p2 = payment_mark_manual(
            bill=bill2,
            amount=Decimal("200.00"),
            created_by=self.user,
        )
        self.assertTrue(p1.reference.startswith("MANUAL-"))
        self.assertNotEqual(p1.reference, p2.reference)

    def test_payment_mark_manual_sets_paid_at(self):
        """payment_mark_manual() records paid_at timestamp."""
        fresh_patient = Patient.objects.create(
            clinic=self.clinic,
            name="Timestamp Patient",
            date_of_birth=datetime.date(1987, 7, 17),
            gender="M",
            phone_number="0700000207",
        )
        bill = bill_get_or_create(patient=fresh_patient, clinic=self.clinic, consultation=None)
        before = timezone.now()
        payment = payment_mark_manual(
            bill=bill,
            amount=Decimal("50.00"),
            created_by=self.user,
        )
        self.assertIsNotNone(payment.paid_at)
        self.assertGreaterEqual(payment.paid_at, before)
