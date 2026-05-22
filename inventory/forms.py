from django import forms
from django.forms import inlineformset_factory

from django_select2.forms import ModelSelect2Widget

from inventory.models import ConsumptionRecord, Item, Location, PurchaseOrder, PurchaseOrderLine, Stock, StockMovement, Supplier


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "number", "expected_date", "notes", "status"]
        widgets = {
            "supplier": ModelSelect2Widget(
                model=Supplier,
                search_fields=["name__icontains"],
                attrs={"data-placeholder": "Search supplier...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "number": forms.TextInput(attrs={"class": "form-control"}),
            "expected_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clinic:
            qs = Supplier.objects.filter(clinic=clinic)
            self.fields["supplier"].queryset = qs
            self.fields["supplier"].widget.queryset = qs


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ["item", "quantity", "unit_price"]
        widgets = {
            "item": ModelSelect2Widget(
                model=Item,
                search_fields=["name__icontains", "sku__icontains"],
                attrs={"data-placeholder": "Search item by name or SKU...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clinic:
            qs = Item.objects.filter(clinic=clinic, is_active=True)
            self.fields["item"].queryset = qs
            self.fields["item"].widget.queryset = qs


PurchaseOrderLineFormset = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderLine,
    form=PurchaseOrderLineForm,
    extra=1,
    can_delete=True,
)


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ["item", "quantity", "from_location", "to_location", "movement_type", "reference", "notes"]
        widgets = {
            "item": ModelSelect2Widget(
                model=Item,
                search_fields=["name__icontains", "sku__icontains"],
                attrs={"data-placeholder": "Search item by name or SKU...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "from_location": ModelSelect2Widget(
                model=Location,
                search_fields=["name__icontains"],
                attrs={"data-placeholder": "From location...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "to_location": ModelSelect2Widget(
                model=Location,
                search_fields=["name__icontains"],
                attrs={"data-placeholder": "To location...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "movement_type": forms.Select(attrs={"class": "form-select"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clinic:
            items = Item.objects.filter(clinic=clinic, is_active=True)
            locations = Location.objects.filter(clinic=clinic)
            self.fields["item"].queryset = items
            self.fields["item"].widget.queryset = items
            self.fields["from_location"].queryset = locations
            self.fields["from_location"].widget.queryset = locations
            self.fields["to_location"].queryset = locations
            self.fields["to_location"].widget.queryset = locations


class ConsumptionForm(forms.ModelForm):
    class Meta:
        model = ConsumptionRecord
        fields = ["from_stock", "consultation", "item", "quantity", "notes"]
        widgets = {
            "item": ModelSelect2Widget(
                model=Item,
                search_fields=["name__icontains"],
                attrs={"data-placeholder": "Search item by name...", "data-minimum-input-length": 0, "class": "form-select"},
            ),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, clinic=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clinic:
            item_qs = Item.objects.filter(clinic=clinic, is_active=True)
            stock_qs = Stock.objects.filter(item__clinic=clinic).select_related("item", "location")
            self.fields["item"].queryset = item_qs
            self.fields["item"].widget.queryset = item_qs
            self.fields["from_stock"].queryset = stock_qs

    def clean(self):
        cleaned = super().clean()
        stock = cleaned.get("from_stock")
        qty = cleaned.get("quantity")
        if stock and qty and stock.quantity < qty:
            raise forms.ValidationError(f"Insufficient stock: {stock.quantity} available, {qty} requested.")
        return cleaned
