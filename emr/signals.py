from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from notification.models import Notification

from .models import LabQueue


@receiver(post_save, sender=LabQueue)
def notify_lab_queue(sender, instance, created, **kwargs):
    if not created:
        return
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            "lab_notifications",
            {
                "type": "send_lab_notification",
                "message": (
                    f"{instance.patient.name} added to lab queue #{instance.queue_number}"
                ),
            },
        )
    clinic = instance.clinic
    if clinic:
        for user in clinic.staff.filter(is_active=True):
            Notification.objects.create(
                user=user,
                title="Patient Sent to Lab",
                body=(
                    f"{instance.patient.name} sent to lab"
                    f" — {instance.lab_test.name if instance.lab_test else 'test'}."
                ),
                url="/emr/",
            )
