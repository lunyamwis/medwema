# inventory/admin.py
from django.contrib import admin
from .models import Supplier, Location, ItemCategory, Item, Stock, StockMovement, PurchaseOrder, PurchaseOrderLine, ConsumptionRecord
from simple_history.admin import SimpleHistoryAdmin

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Item)
class ItemAdmin(SimpleHistoryAdmin):
    list_display = ('name','sku','unit','reorder_level','preferred_supplier')
    search_fields = ('name','sku','barcode')
    list_filter = ('category',)

@admin.register(Stock)
class StockAdmin(SimpleHistoryAdmin):
    list_display = ('item','location','quantity','last_updated')
    search_fields = ('item__name','location__name')

class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('number','supplier','status','created_at')
    inlines = (PurchaseOrderLineInline,)

@admin.register(StockMovement)
class StockMovementAdmin(SimpleHistoryAdmin):
    list_display = ('item','movement_type','quantity','from_location','to_location','created_at')
    search_fields = ('item__name','reference')
    list_filter = ('movement_type',)

@admin.register(ConsumptionRecord)
class ConsumptionRecordAdmin(SimpleHistoryAdmin):
    list_display = ('item','quantity','used_by','used_at','consultation_id')
