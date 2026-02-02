from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from billing.models import Bill, BillItem
from .models import NotificationForSpecialist, DebtCase


def notify_user(clinic, recipient, title, message, url=None):
    NotificationForSpecialist.objects.create(
        clinic=clinic,
        recipient=recipient,
        title=title,
        message=message,
        url=url or "",
    )


def bill_for_service(*, clinic, patient, consultation, service, created_by=None):
    """
    Creates/gets an unpaid bill and adds a line item for the service.
    """
    bill, _ = Bill.objects.get_or_create(
        clinic=clinic,
        patient=patient,
        consultation=consultation,
        is_paid=False,
        defaults={"total_amount": 0},
    )

    item = BillItem.objects.create(
        bill=bill,
        description=service.name,
        quantity=1,
        unit_price=service.price,
        total=service.price,
    )

    # update bill total
    bill.total_amount = sum(i.total for i in bill.items.all())
    bill.save()

    # Open debt case automatically if unpaid
    DebtCase.objects.get_or_create(bill=bill, clinic=clinic, patient=patient)

    return bill, item


def send_external_lab_email(request_obj, attachments=None):
    """
    Sends external lab request email (attachments optional).
    """
    email = EmailMessage(
        subject=request_obj.subject,
        body=request_obj.message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[request_obj.lab_email],
    )
    for f in (attachments or []):
        email.attach_file(f.path)
    email.send(fail_silently=False)

    request_obj.status = "sent"
    request_obj.sent_at = timezone.now()
    request_obj.save()
