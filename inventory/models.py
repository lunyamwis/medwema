from django.contrib.auth import get_user_model
from django.db import models
from simple_history.models import HistoricalRecords

from clinicmanager.models import Clinic
from patient.models import Consultation

User = get_user_model()


class Supplier(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="suppliers", null=True, blank=True)
    name = models.CharField(max_length=255, db_index=True)
    contact = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "name"]),
        ]

    def __str__(self) -> str:
        return self.name


class Location(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="locations", null=True, blank=True)
    name = models.CharField(max_length=150, db_index=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Stock Location"
        verbose_name_plural = "Stock Locations"
        indexes = [
            models.Index(fields=["clinic", "name"]),
        ]

    def __str__(self) -> str:
        return self.name


class ItemCategory(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="item_categories", null=True, blank=True)
    name = models.CharField(max_length=120, db_index=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Item Category"
        verbose_name_plural = "Item Categories"

    def __str__(self) -> str:
        return self.name


class Item(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="items", null=True, blank=True)
    sku = models.CharField(max_length=64, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(ItemCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    unit = models.CharField(max_length=50, default="pcs")
    barcode = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    reorder_level = models.PositiveIntegerField(default=10)
    buying_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    preferred_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "name"]),
            models.Index(fields=["clinic", "is_active"]),
            models.Index(fields=["barcode"]),
        ]

    def total_stock(self):
        return sum(s.quantity for s in self.stocks.all())

    def is_low_stock(self) -> bool:
        return self.total_stock() <= self.reorder_level

    def __str__(self) -> str:
        return f"{self.name} ({self.sku or 'no-sku'})"


class Stock(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="stocks", null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="stocks", null=True, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ("item", "location")
        indexes = [
            models.Index(fields=["item"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self) -> str:
        return f"{self.item} @ {self.location}: {self.quantity}"


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ("IN", "Stock In (Purchase)"),
        ("OUT", "Stock Out (Consumption)"),
        ("TRANSFER", "Transfer Between Locations"),
        ("ADJUST", "Manual Adjustment"),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="movements")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    from_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements_from")
    to_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements_to")
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, db_index=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_movements")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notes = models.TextField(blank=True, null=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["item", "created_at"]),
            models.Index(fields=["movement_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_movement_type_display()} — {self.item.name} × {self.quantity}"


class PurchaseOrder(models.Model):
    STATUS = [
        ("DRAFT", "Draft"),
        ("ORDERED", "Ordered"),
        ("RECEIVED", "Received"),
        ("CANCELLED", "Cancelled"),
    ]

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="purchase_orders", null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_orders")
    number = models.CharField(max_length=100, unique=True, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_orders")
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expected_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clinic", "status"]),
        ]

    def __str__(self) -> str:
        return f"PO {self.number} — {self.supplier or 'No supplier'}"


class PurchaseOrderLine(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="po_lines")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self) -> str:
        return f"{self.item.name} × {self.quantity}"


class ConsumptionRecord(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, null=True, blank=True, related_name="consumptions")
    from_stock = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True, blank=True, related_name="consumptions")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="consumptions")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="consumptions")
    used_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notes = models.TextField(blank=True, null=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-used_at"]
        indexes = [
            models.Index(fields=["item", "used_at"]),
            models.Index(fields=["consultation"]),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} × {self.item.name}"
