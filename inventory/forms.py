# inventory/forms.py
from django import forms
from .models import PurchaseOrder, PurchaseOrderLine, StockMovement, ConsumptionRecord, Item, Stock, Location
from django.forms import inlineformset_factory

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier','number','expected_date','notes','status']

PurchaseOrderLineFormset = inlineformset_factory(PurchaseOrder, PurchaseOrderLine, fields=('item','quantity','unit_price'), extra=1, can_delete=True)

class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['item','quantity','from_location','to_location','movement_type','reference','notes']

class ConsumptionForm(forms.ModelForm):
    class Meta:
        model = ConsumptionRecord
        fields = ['from_stock','consultation','item','quantity','notes']

    def clean(self):
        cleaned = super().clean()
        itm = cleaned.get('item')
        qty = cleaned.get('quantity') or 0
        stock = cleaned.get('from_stock')
        if stock and stock.quantity < qty:
            raise forms.ValidationError("Not enough stock in the selected location.")
        return cleaned
