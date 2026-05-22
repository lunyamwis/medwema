from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Stock


@receiver(post_save, sender=Stock)
def check_low_stock(sender, instance, **kwargs):
    item = instance.item
    total = item.total_stock()
    if total > item.reorder_level:
        return
    recipients = getattr(settings, "INVENTORY_ALERT_EMAILS", [])
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    if recipients and from_email:
        send_mail(
            subject=f"Low stock alert: {item.name}",
            message=(
                f"{item.name} stock is {total} (reorder level: {item.reorder_level})."
                " Please reorder."
            ),
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=True,
        )
