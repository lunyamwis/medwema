import requests
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from clinicmanager.models import Clinic
from .models import PaystackSubaccount

PAYSTACK_BASE = getattr(settings, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')
PAYSTACK_SECRET = getattr(settings, 'PAYSTACK_SECRET_KEY', None)

@receiver(post_save, sender=Clinic)
def create_paystack_subaccount(sender, instance, created, **kwargs):
    if not created:
        return
    if not PAYSTACK_SECRET:
        return
    # Build payload per Paystack API v1 (example)
    payload = {
        "business_name": instance.name,
        "settlement_bank": "ACCESS_BANK",  # required by Paystack - choose default or map from clinic
        "account_number": "0000000000",    # placeholder - you might not have bank acc immediately
        "percentage_charge": 0,
        # Additional optional fields...
    }
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}",
        "Content-Type": "application/json",
    }
    url = f"{PAYSTACK_BASE}/subaccount"
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        data = r.json()
        if r.status_code in (200,201) and data.get('status'):
            sub = PaystackSubaccount.objects.create(
                clinic=instance,
                subaccount_code=data['data'].get('subaccount_code'),
                business_name=data['data'].get('business_name'),
                raw_response=data
            )
        else:
            # store error for manual follow-up
            PaystackSubaccount.objects.create(
                clinic=instance,
                raw_response=data
            )
    except Exception as e:
        PaystackSubaccount.objects.create(clinic=instance, raw_response={'error': str(e)})
