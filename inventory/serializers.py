from rest_framework import serializers
from inventory.models import ConsumptionRecord, Item, Stock, StockMovement

class ItemSerializer(serializers.ModelSerializer):
    total_stock = serializers.DecimalField(max_digits=12, decimal_places=2, source='total_stock', read_only=True)
    class Meta:
        model = Item
        fields = ['id','sku','name','barcode','unit','reorder_level','total_stock']

class StockSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)
    class Meta:
        model = Stock
        fields = ['id','item','location','quantity','last_updated']

class ConsumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsumptionRecord
        fields = ['id','consultation','from_stock','item','quantity','used_by','used_at','notes']
        read_only_fields = ['used_by','used_at']
