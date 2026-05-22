from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from inventory.models import (
    ConsumptionRecord,
    Item,
    PurchaseOrder,
    PurchaseOrderLine,
    Stock,
    StockMovement,
)
from patient.models import Consultation


@transaction.atomic
def stock_receive_po(*, po: PurchaseOrder, location) -> None:
    for line in po.lines.select_related("item").all():
        stock, _ = Stock.objects.get_or_create(item=line.item, location=location)
        stock.quantity += line.quantity
        stock.save(update_fields=["quantity", "last_updated"])
        StockMovement.objects.create(
            item=line.item,
            quantity=line.quantity,
            to_location=location,
            movement_type="IN",
            reference=f"PO-{po.number}",
        )
        line.received_quantity = line.quantity
        line.save(update_fields=["received_quantity"])
    po.status = "RECEIVED"
    po.save(update_fields=["status"])


@transaction.atomic
def stock_transfer(
    *,
    item: Item,
    from_location,
    to_location,
    quantity: Decimal,
    created_by=None,
    notes: str = "",
) -> StockMovement:
    from_stock = Stock.objects.get(item=item, location=from_location)
    if from_stock.quantity < quantity:
        raise ValueError(f"Insufficient stock: {from_stock.quantity} available, {quantity} requested.")
    from_stock.quantity -= quantity
    from_stock.save(update_fields=["quantity", "last_updated"])

    to_stock, _ = Stock.objects.get_or_create(item=item, location=to_location)
    to_stock.quantity += quantity
    to_stock.save(update_fields=["quantity", "last_updated"])

    return StockMovement.objects.create(
        item=item,
        quantity=quantity,
        from_location=from_location,
        to_location=to_location,
        movement_type="TRANSFER",
        created_by=created_by,
        notes=notes,
    )


@transaction.atomic
def stock_consume(
    *,
    item: Item,
    from_stock: Stock,
    quantity: Decimal,
    consultation: Consultation | None = None,
    used_by=None,
    notes: str = "",
) -> ConsumptionRecord:
    if from_stock.quantity < quantity:
        raise ValueError(f"Insufficient stock: {from_stock.quantity} available, {quantity} requested.")
    from_stock.quantity -= quantity
    from_stock.save(update_fields=["quantity", "last_updated"])

    StockMovement.objects.create(
        item=item,
        quantity=quantity,
        from_location=from_stock.location,
        movement_type="OUT",
        created_by=used_by,
        notes=notes,
    )

    return ConsumptionRecord.objects.create(
        consultation=consultation,
        from_stock=from_stock,
        item=item,
        quantity=quantity,
        used_by=used_by,
        notes=notes,
    )


def stock_adjust(
    *,
    item: Item,
    location,
    new_quantity: Decimal,
    created_by=None,
    notes: str = "",
) -> Stock:
    stock, _ = Stock.objects.get_or_create(item=item, location=location)
    diff = new_quantity - stock.quantity
    stock.quantity = new_quantity
    stock.save(update_fields=["quantity", "last_updated"])
    if diff != 0:
        StockMovement.objects.create(
            item=item,
            quantity=abs(diff),
            to_location=location if diff > 0 else None,
            from_location=location if diff < 0 else None,
            movement_type="ADJUST",
            created_by=created_by,
            notes=notes or f"Adjustment by {created_by}",
        )
    return stock
