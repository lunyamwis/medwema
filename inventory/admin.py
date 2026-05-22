from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
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


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "clinic")
    search_fields = ("name", "email")
    list_filter = ("clinic",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "clinic", "description")
    search_fields = ("name",)


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "clinic")
    search_fields = ("name",)


@admin.register(Item)
class ItemAdmin(SimpleHistoryAdmin):
    list_display = (
        "name",
        "sku",
        "unit",
        "buying_price",
        "price",
        "reorder_level",
        "is_active",
        "clinic_name",
        "stock_level",
    )
    search_fields = ("name", "sku", "barcode")
    list_filter = ("category", "is_active", "clinic")
    list_editable = ("is_active",)

    @admin.display(description="Clinic", ordering="clinic__name")
    def clinic_name(self, obj):
        return obj.clinic.name if obj.clinic else "-"

    @admin.display(description="Stock Level")
    def stock_level(self, obj):
        return obj.total_stock()


@admin.register(Stock)
class StockAdmin(SimpleHistoryAdmin):
    list_display = ("item_name", "location", "quantity", "last_updated")
    search_fields = ("item__name", "location__name")
    list_select_related = ("item", "location")

    @admin.display(description="Item", ordering="item__name")
    def item_name(self, obj):
        return obj.item.name if obj.item else "-"


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "supplier", "status", "created_at", "expected_date")
    list_filter = ("status", "created_at")
    search_fields = ("number", "supplier__name")
    inlines = (PurchaseOrderLineInline,)


@admin.register(StockMovement)
class StockMovementAdmin(SimpleHistoryAdmin):
    list_display = (
        "item_name",
        "movement_type",
        "quantity",
        "from_location",
        "to_location",
        "created_at",
    )
    search_fields = ("item__name", "reference")
    list_filter = ("movement_type", "created_at")

    @admin.display(description="Item", ordering="item__name")
    def item_name(self, obj):
        return obj.item.name if obj.item else "-"


@admin.register(ConsumptionRecord)
class ConsumptionRecordAdmin(SimpleHistoryAdmin):
    list_display = ("item_name", "quantity", "used_by", "used_at")
    search_fields = ("item__name",)
    list_filter = ("used_at",)

    @admin.display(description="Item", ordering="item__name")
    def item_name(self, obj):
        return obj.item.name if obj.item else "-"
