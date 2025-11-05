# inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Stock, Item
from django.core.mail import send_mail
from django.conf import settings

@receiver(post_save, sender=Stock)
def check_low_stock(sender, instance, **kwargs):
    item = instance.item
    total = item.total_stock()
    if total <= item.reorder_level:
        # Example: send email to pharmacy manager (settings.INVENTORY_ALERT_EMAILS)
        recipients = getattr(settings, 'INVENTORY_ALERT_EMAILS', [])
        if recipients:
            send_mail(
                subject=f'Low stock: {item.name}',
                message=f'{item.name} stock is low ({total}). Please reorder or check supplier.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
            )
