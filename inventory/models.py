# inventory/models.py

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from simple_history.models import HistoricalRecords
from patient.models import Consultation

User = get_user_model()

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    """Physical location (Pharmacy, Main Store, Lab store)."""
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Stock Location"
        verbose_name_plural = "Stock Locations"

    def __str__(self):
        return self.name

class ItemCategory(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True,null=True)

    def __str__(self):
        return self.name



class Item(models.Model):
    sku = models.CharField(max_length=64, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(ItemCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    unit = models.CharField(max_length=50, default='pcs')
    barcode = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    reorder_level = models.PositiveIntegerField(default=10)
    buying_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    preferred_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} ({self.sku or 'no-sku'})"

# Stock model unchanged, but add history
class Stock(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='stocks', null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='stocks',null=True, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('item', 'location')

# StockMovement existing model - add history
class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Stock In (Purchase)'),
        ('OUT', 'Stock Out (Consumption)'),
        ('TRANSFER', 'Transfer Between Locations'),
        ('ADJUST', 'Manual Adjustment'),
    ]
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='movements')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    from_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements_from')
    to_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements_to')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    reference = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']



class PurchaseOrder(models.Model):
    STATUS = [
        ('DRAFT', 'Draft'),
        ('ORDERED', 'Ordered'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    number = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    expected_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"PO {self.number} - {self.supplier or 'No supplier'}"


class PurchaseOrderLine(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='lines')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"

# Optional: simple consumption record linking to consultation
class ConsumptionRecord(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, null=True, blank=True, related_name='consumptions')
    from_stock = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.quantity} {self.item.name} used for consult {self.consultation.id or '-'}"
