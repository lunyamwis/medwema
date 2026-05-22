from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from billing.models import Bill, BillItem, Payment
from clinicmanager.models import Clinic
from patient.models import Consultation, Patient


def bill_get_or_create(
    *,
    patient: Patient,
    clinic: Clinic,
    consultation: Consultation | None = None,
) -> Bill:
    if consultation:
        bill, _ = Bill.objects.get_or_create(
            consultation=consultation,
            clinic=clinic,
            defaults={"patient": patient},
        )
    else:
        bill = Bill.objects.create(patient=patient, clinic=clinic)
    return bill


def bill_add_item(
    *,
    bill: Bill,
    description: str,
    quantity: int = 1,
    unit_price: Decimal,
) -> BillItem:
    item = BillItem.objects.create(
        bill=bill,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
    )
    _recalculate_bill_total(bill)
    return item


def _recalculate_bill_total(bill: Bill) -> None:
    total = sum(i.total for i in bill.items.all())
    bill.total_amount = total
    bill.save(update_fields=["total_amount", "updated_at"])


@transaction.atomic
def payment_mark_manual(*, bill: Bill, amount: Decimal, created_by, payment_method: str = "CASH") -> Payment:
    import uuid
    reference = f"MANUAL-{uuid.uuid4().hex[:10].upper()}"
    payment = Payment.objects.create(
        bill=bill,
        reference=reference,
        amount=amount,
        payment_method=payment_method,
        created_by=created_by,
    )
    payment.mark_as_paid(manual=True)
    return payment


def bill_list_unpaid(*, clinic: Clinic):
    return (
        Bill.objects.filter(clinic=clinic, is_paid=False)
        .select_related("patient", "consultation")
        .prefetch_related("items")
        .order_by("-created_at")
    )


def bill_list_paid(*, clinic: Clinic):
    return (
        Bill.objects.filter(clinic=clinic, is_paid=True)
        .select_related("patient", "consultation")
        .order_by("-updated_at")
    )


def revenue_in_range(*, clinic: Clinic, start, end) -> Decimal:
    from django.db.models import Sum
    result = (
        Payment.objects.filter(
            bill__clinic=clinic,
            status__in=["success", "manual"],
            paid_at__date__gte=start,
            paid_at__date__lte=end,
        ).aggregate(total=Sum("amount"))["total"]
    )
    return result or Decimal("0.00")
