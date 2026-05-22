from __future__ import annotations

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from clinicmanager.models import Clinic
from inventory.models import (
    ConsumptionRecord,
    Item,
    ItemCategory,
    Location,
    Stock,
    StockMovement,
)
from inventory.services import stock_consume, stock_transfer
from patient.models import Consultation, Patient

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

class BaseInventoryTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="invuser", password="pass123")
        cls.clinic = Clinic.objects.create(name="Inventory Clinic", created_by=cls.user)
        cls.user.clinics.add(cls.clinic)

        cls.category = ItemCategory.objects.create(clinic=cls.clinic, name="Medicines")
        cls.location_a = Location.objects.create(clinic=cls.clinic, name="Pharmacy A")
        cls.location_b = Location.objects.create(clinic=cls.clinic, name="Pharmacy B")

        cls.item = Item.objects.create(
            clinic=cls.clinic,
            name="Amoxicillin 500mg",
            sku="AMX500",
            category=cls.category,
            unit="tabs",
            reorder_level=20,
            price=Decimal("15.00"),
        )

        cls.patient = Patient.objects.create(
            clinic=cls.clinic,
            name="Inventory Patient",
            date_of_birth=datetime.date(1990, 1, 1),
            gender="M",
            phone_number="0700000300",
        )
        cls.consultation = Consultation.objects.create(patient=cls.patient)


# ---------------------------------------------------------------------------
# Item model tests
# ---------------------------------------------------------------------------

class ItemModelTests(BaseInventoryTestCase):

    def test_total_stock_no_stocks(self):
        """total_stock() returns 0 when the item has no Stock records."""
        item = Item.objects.create(
            clinic=self.clinic,
            name="Orphan Item",
            sku="ORP001",
            reorder_level=5,
        )
        self.assertEqual(item.total_stock(), 0)

    def test_total_stock_with_stocks(self):
        """total_stock() sums quantities across all Stock locations."""
        item = Item.objects.create(
            clinic=self.clinic,
            name="Multi-Location Item",
            sku="MLI001",
            reorder_level=10,
        )
        Stock.objects.create(item=item, location=self.location_a, quantity=Decimal("30"))
        Stock.objects.create(item=item, location=self.location_b, quantity=Decimal("20"))
        self.assertEqual(item.total_stock(), 50)

    def test_is_low_stock_true(self):
        """is_low_stock() returns True when total stock is at or below reorder_level."""
        item = Item.objects.create(
            clinic=self.clinic,
            name="Low Stock Item",
            sku="LSI001",
            reorder_level=25,
        )
        Stock.objects.create(item=item, location=self.location_a, quantity=Decimal("25"))
        self.assertTrue(item.is_low_stock())

    def test_is_low_stock_true_below_reorder(self):
        """is_low_stock() returns True when total stock is below the reorder level."""
        item = Item.objects.create(
            clinic=self.clinic,
            name="Very Low Item",
            sku="VLI001",
            reorder_level=50,
        )
        Stock.objects.create(item=item, location=self.location_a, quantity=Decimal("10"))
        self.assertTrue(item.is_low_stock())

    def test_is_low_stock_false(self):
        """is_low_stock() returns False when total stock exceeds the reorder level."""
        item = Item.objects.create(
            clinic=self.clinic,
            name="Adequate Stock Item",
            sku="ASI001",
            reorder_level=20,
        )
        Stock.objects.create(item=item, location=self.location_a, quantity=Decimal("100"))
        self.assertFalse(item.is_low_stock())

    def test_item_str_includes_name_and_sku(self):
        """__str__ contains both the item name and its SKU."""
        self.assertIn("Amoxicillin 500mg", str(self.item))
        self.assertIn("AMX500", str(self.item))


# ---------------------------------------------------------------------------
# InventoryService tests — stock_consume
# ---------------------------------------------------------------------------

class StockConsumeServiceTests(BaseInventoryTestCase):

    def _make_stock(self, quantity=Decimal("100")):
        stock, _ = Stock.objects.get_or_create(
            item=self.item,
            location=self.location_a,
            defaults={"quantity": quantity},
        )
        stock.quantity = quantity
        stock.save(update_fields=["quantity"])
        return stock

    def test_stock_consume_reduces_quantity(self):
        """stock_consume() deducts the consumed quantity from the Stock record."""
        stock = self._make_stock(Decimal("100"))
        stock_consume(
            item=self.item,
            from_stock=stock,
            quantity=Decimal("30"),
            used_by=self.user,
        )
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, Decimal("70"))

    def test_stock_consume_creates_consumption_record(self):
        """stock_consume() records the consumption in ConsumptionRecord."""
        stock = self._make_stock(Decimal("50"))
        record = stock_consume(
            item=self.item,
            from_stock=stock,
            quantity=Decimal("10"),
            consultation=self.consultation,
            used_by=self.user,
            notes="Given to patient",
        )
        self.assertIsNotNone(record.pk)
        self.assertEqual(record.quantity, Decimal("10"))
        self.assertEqual(record.item, self.item)
        self.assertEqual(record.consultation, self.consultation)
        self.assertEqual(record.notes, "Given to patient")

    def test_stock_consume_creates_stock_movement(self):
        """stock_consume() records an OUT movement in StockMovement."""
        stock = self._make_stock(Decimal("80"))
        stock_consume(
            item=self.item,
            from_stock=stock,
            quantity=Decimal("15"),
            used_by=self.user,
        )
        movement = StockMovement.objects.filter(
            item=self.item,
            movement_type="OUT",
            quantity=Decimal("15"),
        ).first()
        self.assertIsNotNone(movement)

    def test_stock_consume_raises_if_insufficient(self):
        """stock_consume() raises ValueError when requested quantity exceeds available stock."""
        stock = self._make_stock(Decimal("5"))
        with self.assertRaises(ValueError) as ctx:
            stock_consume(
                item=self.item,
                from_stock=stock,
                quantity=Decimal("50"),
                used_by=self.user,
            )
        self.assertIn("Insufficient", str(ctx.exception))

    def test_stock_consume_raises_does_not_modify_stock(self):
        """When stock_consume() raises ValueError the stock quantity is left unchanged."""
        stock = self._make_stock(Decimal("5"))
        try:
            stock_consume(
                item=self.item,
                from_stock=stock,
                quantity=Decimal("50"),
                used_by=self.user,
            )
        except ValueError:
            pass
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, Decimal("5"))


# ---------------------------------------------------------------------------
# InventoryService tests — stock_transfer
# ---------------------------------------------------------------------------

class StockTransferServiceTests(BaseInventoryTestCase):

    def _setup_transfer_stocks(self, from_qty=Decimal("100"), to_qty=Decimal("0")):
        from_stock, _ = Stock.objects.get_or_create(
            item=self.item,
            location=self.location_a,
            defaults={"quantity": from_qty},
        )
        from_stock.quantity = from_qty
        from_stock.save(update_fields=["quantity"])

        to_stock, _ = Stock.objects.get_or_create(
            item=self.item,
            location=self.location_b,
            defaults={"quantity": to_qty},
        )
        to_stock.quantity = to_qty
        to_stock.save(update_fields=["quantity"])
        return from_stock, to_stock

    def test_stock_transfer_moves_quantity(self):
        """stock_transfer() decreases from_location and increases to_location by the given qty."""
        from_stock, to_stock = self._setup_transfer_stocks(
            from_qty=Decimal("100"),
            to_qty=Decimal("10"),
        )
        stock_transfer(
            item=self.item,
            from_location=self.location_a,
            to_location=self.location_b,
            quantity=Decimal("40"),
            created_by=self.user,
        )
        from_stock.refresh_from_db()
        to_stock.refresh_from_db()
        self.assertEqual(from_stock.quantity, Decimal("60"))
        self.assertEqual(to_stock.quantity, Decimal("50"))

    def test_stock_transfer_creates_movement_record(self):
        """stock_transfer() creates a TRANSFER StockMovement."""
        from_stock, _ = self._setup_transfer_stocks()
        stock_transfer(
            item=self.item,
            from_location=self.location_a,
            to_location=self.location_b,
            quantity=Decimal("25"),
            created_by=self.user,
            notes="Replenish pharmacy B",
        )
        movement = StockMovement.objects.filter(
            item=self.item,
            movement_type="TRANSFER",
            quantity=Decimal("25"),
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.from_location, self.location_a)
        self.assertEqual(movement.to_location, self.location_b)

    def test_stock_transfer_raises_if_insufficient(self):
        """stock_transfer() raises ValueError when from_stock has less than requested."""
        self._setup_transfer_stocks(from_qty=Decimal("10"), to_qty=Decimal("0"))
        with self.assertRaises(ValueError) as ctx:
            stock_transfer(
                item=self.item,
                from_location=self.location_a,
                to_location=self.location_b,
                quantity=Decimal("999"),
                created_by=self.user,
            )
        self.assertIn("Insufficient", str(ctx.exception))

    def test_stock_transfer_raises_does_not_modify_stocks(self):
        """When stock_transfer() raises the source and destination are left unchanged."""
        from_stock, to_stock = self._setup_transfer_stocks(
            from_qty=Decimal("10"),
            to_qty=Decimal("5"),
        )
        try:
            stock_transfer(
                item=self.item,
                from_location=self.location_a,
                to_location=self.location_b,
                quantity=Decimal("999"),
                created_by=self.user,
            )
        except ValueError:
            pass
        from_stock.refresh_from_db()
        to_stock.refresh_from_db()
        self.assertEqual(from_stock.quantity, Decimal("10"))
        self.assertEqual(to_stock.quantity, Decimal("5"))

    def test_stock_transfer_creates_to_stock_if_not_exists(self):
        """stock_transfer() creates the destination Stock record if it does not yet exist."""
        # Ensure from_stock exists but to_stock does not
        from_stock, _ = Stock.objects.get_or_create(
            item=self.item,
            location=self.location_a,
            defaults={"quantity": Decimal("200")},
        )
        from_stock.quantity = Decimal("200")
        from_stock.save(update_fields=["quantity"])
        # Remove to_stock if it happens to exist from earlier tests
        Stock.objects.filter(item=self.item, location=self.location_b).delete()

        stock_transfer(
            item=self.item,
            from_location=self.location_a,
            to_location=self.location_b,
            quantity=Decimal("50"),
            created_by=self.user,
        )
        to_stock = Stock.objects.get(item=self.item, location=self.location_b)
        self.assertEqual(to_stock.quantity, Decimal("50"))
