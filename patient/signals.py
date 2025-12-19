from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Queue
from chat.models import ChatMessage
from webpush import send_user_notification
from authentication.models import User  
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from notification.models import Notification

@receiver(post_save, sender=Queue)
def notify_lab_queue(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "patients",  # channel group
            {
                "type": "patient_alert",
                "message": f"New patient: {instance.patient.name}"
            }
        )
        payload = {
            "head": "New Patient Added",
            "body": f"{instance.patient.name} added to the queue.",
            # "icon": "/static/icons/alert.png",
            "url": "/patients/doctors/"
        }

        user = User.objects.get(username='baharimedicalclinic')
        # payload = {"head": "Patient Arrival!", "body": "A new patient has arrived!"}
        send_user_notification(user=user, payload=payload, ttl=1000)

        # Also create a Notification entry in the database
        Notification.objects.create(
            user=user,
            title="New Patient Added",
            body=f"{instance.patient.name} added to the queue.",
            url="/patients/doctors/"
        )



@receiver(post_save, sender=ChatMessage)
def notify_lab_queue(sender, instance, created, **kwargs):
    if created:
        
        payload = {
            "head": "New Message Arrived",
            "body": f"A message has arrived for chat room {instance.room.name}",
            # "icon": "/static/icons/alert.png",
            "url": "/chat/"
        }

        user = User.objects.get(username='baharimedicalclinic')
        # payload = {"head": "Patient Arrival!", "body": "A new patient has arrived!"}
        send_user_notification(user=user, payload=payload, ttl=1000)

        # Also create a Notification entry in the database
        Notification.objects.create(
            user=user,
            title="New Message Arrived",
            body=f"A message has arrived for chat room {instance.room.name}",
            url="/chat/"
        )