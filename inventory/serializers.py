from __future__ import annotations

from rest_framework import serializers

from inventory.models import (
    ConsumptionRecord,
    Item,
    ItemCategory,
    Location,
    PurchaseOrder,
    PurchaseOrderLine,
    Stock,
    StockMovement,
    Supplier,
)


class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = ["id", "name", "description"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact", "email", "phone", "address", "notes"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name", "description"]


class ItemSerializer(serializers.ModelSerializer):
    total_stock = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    supplier_name = serializers.CharField(source="preferred_supplier.name", read_only=True, default=None)

    class Meta:
        model = Item
        fields = [
            "id", "sku", "name", "description", "barcode", "unit",
            "category", "category_name", "reorder_level",
            "buying_price", "price",
            "preferred_supplier", "supplier_name",
            "is_active", "created_at", "total_stock",
        ]


class StockSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True, default=None)

    class Meta:
        model = Stock
        fields = ["id", "item", "item_name", "location", "location_name", "quantity", "last_updated"]


class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = StockMovement
        fields = [
            "id", "item", "item_name", "quantity",
            "from_location", "to_location", "movement_type",
            "reference", "created_by", "created_by_name",
            "created_at", "notes",
        ]
        read_only_fields = ["created_by", "created_at"]


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = ["id", "item", "item_name", "quantity", "unit_price", "received_quantity"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "number", "supplier", "supplier_name",
            "status", "status_display", "created_at", "expected_date",
            "notes", "lines",
        ]
        read_only_fields = ["number", "created_by", "created_at"]


class ConsumptionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = ConsumptionRecord
        fields = [
            "id", "consultation", "from_stock", "item", "item_name",
            "quantity", "used_by", "used_at", "notes",
        ]
        read_only_fields = ["used_by", "used_at"]
