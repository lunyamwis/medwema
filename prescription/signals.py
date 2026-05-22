from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

from inventory.models import ConsumptionRecord, Stock, StockMovement

from .models import Prescription


@receiver(post_save, sender=Prescription)
def prescription_post_save(sender, instance, created, **kwargs):
    if not created:
        return

    item = instance.item
    qty = instance.quantity
    consultation = instance.consultation

    if not item or not qty:
        return

    with transaction.atomic():
        # Deduct from the first location that has sufficient stock.
        stock = Stock.objects.filter(item=item, quantity__gte=qty).order_by("id").first()
        if stock:
            stock.quantity -= qty
            stock.save(update_fields=["quantity"])
            StockMovement.objects.create(
                item=item,
                quantity=qty,
                from_location=stock.location,
                to_location=None,
                movement_type="OUT",
                reference=f"PRESC-{consultation.id}" if consultation else "PRESC",
                created_by=instance.prescribed_by,
            )
            ConsumptionRecord.objects.create(
                consultation=consultation,
                from_stock=stock,
                item=item,
                quantity=qty,
                used_by=instance.prescribed_by,
            )

        # Add a bill line item; Bill.total_amount is recomputed from the items
        # aggregate to avoid double-counting.
        if consultation:
            from billing.models import Bill, BillItem

            try:
                bill = Bill.objects.filter(
                    patient=consultation.patient, is_paid=False
                ).latest("created_at")
                BillItem.objects.create(
                    bill=bill,
                    description=item.name,
                    quantity=qty,
                    unit_price=item.price,
                )
                total = bill.items.aggregate(t=Sum("total"))["t"] or 0
                Bill.objects.filter(pk=bill.pk).update(total_amount=total)
            except Bill.DoesNotExist:
                pass
