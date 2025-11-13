from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LabQueue
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from webpush import send_user_notification
from authentication.models import User  

@receiver(post_save, sender=LabQueue)
def notify_lab_queue(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        print("New LabQueue entry created, sending notification...")
        async_to_sync(channel_layer.group_send)(
            "lab_notifications",
            {
                "type": "send_lab_notification",
                "message": f"New patient {instance.patient.name} added to queue #{instance.queue_number}"
            }
        )

        # payload = {
        #     "head": "New Patient Added",
        #     "body": f"{instance.patient.name} added to the queue.",
        #     "icon": "/static/icons/alert.png",
        #     "url": "/lab/dashboard/"
        # }

        # attendants = User.objects.filter(username='baharimedicalclinic')
        # for attendant in attendants:
        #     send_user_notification(user=attendant, payload=payload, ttl=1000)
