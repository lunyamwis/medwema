# prescription/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Prescription
from inventory.models import ConsumptionRecord, Stock, StockMovement
from billing.models import Bill, BillItem
from django.db import transaction

@receiver(post_save, sender=Prescription)
def prescription_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    consultation = instance.consultation
    item = instance.item
    qty = instance.quantity

    # create consumption record and adjust stock (choose proper stock location)
    # get preferred stock (example: Pharmacy)
    default_loc = Stock.objects.filter(item=item).first()
    if default_loc:
        # subtract stock
        default_loc.quantity = default_loc.quantity - qty
        default_loc.save()
        StockMovement.objects.create(
            item=item,
            quantity=qty,
            from_location=default_loc.location,
            to_location=None,
            movement_type='OUT',
            reference=f'PRESC-{consultation.id}',
            created_by=instance.prescribed_by
        )
        ConsumptionRecord.objects.create(
            consultation=consultation,
            from_stock=default_loc,
            item=item,
            quantity=qty,
            used_by=instance.prescribed_by
        )
    # create or update bill
    # import pdb;pdb.set_trace()
    bill, created_bill = Bill.objects.get_or_create(
        consultation=consultation,
        defaults={'patient':consultation.patient, 'clinic': consultation.patient.clinic}
    )
    unit_price = item.price
    bi = BillItem.objects.create(
        bill=bill,
        description=item.name,
        quantity=qty,
        unit_price=unit_price
    )
    bill.total_amount += item.price
    bill.save()
