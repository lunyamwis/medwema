from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from notification.models import Notification

from .models import Queue


def _get_clinic_users(clinic):
    """Return all active users belonging to the clinic."""
    return clinic.staff.filter(is_active=True) if clinic else []


@receiver(post_save, sender=Queue)
def notify_patient_queue(sender, instance, created, **kwargs):
    if not created:
        return
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            "patients",
            {"type": "patient_alert", "message": f"New patient: {instance.patient.name}"},
        )
    clinic = instance.clinic
    if clinic:
        for user in _get_clinic_users(clinic):
            Notification.objects.create(
                user=user,
                title="New Patient Added",
                body=f"{instance.patient.name} added to queue #{instance.queue_number}.",
                url="/patients/",
            )


@receiver(post_save, sender="chat.ChatMessage")
def notify_chat_message(sender, instance, created, **kwargs):
    if not created:
        return
    room = instance.room
    clinic = getattr(room, "clinic", None)
    if clinic:
        for user in _get_clinic_users(clinic):
            if user != instance.sender:
                Notification.objects.create(
                    user=user,
                    title="New Message",
                    body=f"New message in {room.name}",
                    url="/chat/",
                )
