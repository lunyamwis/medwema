import requests
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from clinicmanager.models import ClinicBankDetails

from .models import PaystackSubaccount

PAYSTACK_BASE = getattr(settings, "PAYSTACK_BASE_URL", "https://api.paystack.co")
PAYSTACK_SECRET = getattr(settings, "PAYSTACK_SECRET_KEY", None)


@receiver(post_save, sender=ClinicBankDetails)
def create_paystack_subaccount(sender, instance, created, **kwargs):
    if not created:
        return
    if not PAYSTACK_SECRET:
        return

    payload = {
        "business_name": instance.clinic.name,
        "settlement_bank": instance.bank_name,
        "account_number": instance.account_number,
        "percentage_charge": 0,
    }
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}",
        "Content-Type": "application/json",
    }
    url = f"{PAYSTACK_BASE}/subaccount"
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        data = r.json()
        if r.status_code in (200, 201) and data.get("status"):
            PaystackSubaccount.objects.create(
                clinic=instance.clinic,
                subaccount_code=data["data"].get("subaccount_code"),
                business_name=data["data"].get("business_name"),
                raw_response=data,
            )
        else:
            PaystackSubaccount.objects.create(
                clinic=instance.clinic,
                raw_response=data,
            )
    except Exception as e:
        PaystackSubaccount.objects.create(
            clinic=instance.clinic,
            raw_response={"error": str(e)},
        )
