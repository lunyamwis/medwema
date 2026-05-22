from __future__ import annotations

import logging

from django.contrib import messages

logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from inventory.forms import (
    PurchaseOrderForm,
    PurchaseOrderLineFormset,
    StockMovementForm,
    ConsumptionForm,
)
from inventory.models import (
    Item,
    Stock,
    StockMovement,
    PurchaseOrder,
    PurchaseOrderLine,
    Location,
    ItemCategory,
    Supplier,
    ConsumptionRecord,
)
from inventory.serializers import ItemSerializer, StockSerializer, ConsumptionSerializer
from inventory.services import stock_receive_po, stock_consume


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_clinic(user):
    return user.clinics.select_related().last()


# ─── REST Viewsets ────────────────────────────────────────────────────────────

class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category__id"]
    search_fields = ["name", "sku", "barcode"]
    ordering_fields = ["name", "reorder_level"]

    def get_queryset(self):
        clinic = self.request.user.clinics.last()
        return Item.objects.filter(clinic=clinic).order_by("name")


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["item__name", "location__name"]

    def get_queryset(self):
        clinic = self.request.user.clinics.last()
        return Stock.objects.filter(item__clinic=clinic).select_related("item", "location")


class ConsumptionViewSet(viewsets.ModelViewSet):
    serializer_class = ConsumptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        clinic = self.request.user.clinics.last()
        return ConsumptionRecord.objects.filter(item__clinic=clinic).select_related(
            "item", "from_stock", "consultation"
        )

    def perform_create(self, serializer):
        cr = serializer.save(used_by=self.request.user)
        if cr.from_stock:
            stock = cr.from_stock
            stock.quantity -= cr.quantity
            stock.save()
            StockMovement.objects.create(
                item=cr.item,
                quantity=cr.quantity,
                from_location=stock.location,
                to_location=None,
                movement_type="OUT",
                reference=f"CONSULT-{cr.consultation.id if cr.consultation else ''}",
                created_by=self.request.user,
            )


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    clinic = _get_clinic(request.user)

    all_items = Item.objects.filter(clinic=clinic, is_active=True).prefetch_related("stocks")
    low_stock_items = [item for item in all_items if item.is_low_stock()]
    total_items_count = Item.objects.filter(clinic=clinic).count()

    recent_movements = (
        StockMovement.objects.filter(item__clinic=clinic)
        .select_related("item", "from_location", "to_location", "created_by")
        .order_by("-created_at")[:15]
    )

    pos_pending_count = PurchaseOrder.objects.filter(
        clinic=clinic, status__in=["DRAFT", "ORDERED"]
    ).count()

    today = timezone.localdate()
    movements_today = StockMovement.objects.filter(
        item__clinic=clinic, created_at__date=today
    ).count()

    context = {
        "low_stock_items": low_stock_items,
        "recent_movements": recent_movements,
        "total_items_count": total_items_count,
        "pos_pending_count": pos_pending_count,
        "movements_today": movements_today,
    }
    return render(request, "inventory/dashboard.html", context)


# ─── Items ────────────────────────────────────────────────────────────────────

@login_required
def item_list(request):
    clinic = _get_clinic(request.user)
    q = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")

    qs = Item.objects.filter(clinic=clinic).select_related("category", "preferred_supplier")

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q))

    if category_id:
        qs = qs.filter(category__id=category_id)

    categories = ItemCategory.objects.filter(clinic=clinic)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "query": q,
        "categories": categories,
        "selected_category": category_id,
    }
    return render(request, "inventory/item_list.html", context)


@login_required
def item_detail(request, pk):
    clinic = _get_clinic(request.user)
    item = get_object_or_404(Item, pk=pk, clinic=clinic)
    stocks = item.stocks.select_related("location").all()
    movements = (
        item.movements.select_related("from_location", "to_location", "created_by")
        .order_by("-created_at")[:20]
    )
    context = {
        "item": item,
        "stocks": stocks,
        "movements": movements,
    }
    return render(request, "inventory/item_detail.html", context)


# ─── Purchase Orders ──────────────────────────────────────────────────────────

@login_required
def po_list(request):
    clinic = _get_clinic(request.user)
    q = request.GET.get("q", "").strip()

    qs = PurchaseOrder.objects.filter(clinic=clinic).select_related("supplier").prefetch_related("lines")

    if q:
        qs = qs.filter(
            Q(supplier__name__icontains=q) | Q(number__icontains=q)
        )

    paginator = Paginator(qs.order_by("-created_at"), 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "query": q,
    }
    return render(request, "inventory/po_list.html", context)


@login_required
def create_po(request):
    clinic = _get_clinic(request.user)

    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, clinic=clinic)
        formset = PurchaseOrderLineFormset(request.POST, form_kwargs={"clinic": clinic})
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                po = form.save(commit=False)
                po.clinic = clinic
                po.created_by = request.user
                po.number = (
                    f"PO{timezone.now().strftime('%Y%m%d')}-"
                    f"{PurchaseOrder.objects.count() + 1:04d}"
                )
                po.save()
                formset.instance = po
                formset.save()
            logger.info("PO %s created by %s", po.number, request.user.username)
            messages.success(request, f"Purchase order {po.number} created.")
            return redirect("po_list")
    else:
        form = PurchaseOrderForm(clinic=clinic)
        formset = PurchaseOrderLineFormset(form_kwargs={"clinic": clinic})

    return render(request, "inventory/po_form.html", {"form": form, "formset": formset})


@login_required
def receive_po(request, pk):
    clinic = _get_clinic(request.user)
    po = get_object_or_404(PurchaseOrder, pk=pk, clinic=clinic)

    if request.method == "POST":
        if po.status in ("RECEIVED", "CANCELLED"):
            logger.warning("Attempt to receive PO %s with status %s by %s", po.number, po.status, request.user.username)
            messages.error(request, f"PO {po.number} cannot be received (status: {po.status}).")
            return redirect("po_list")

        default_location, _ = Location.objects.get_or_create(
            clinic=clinic, name="Main Store"
        )
        with transaction.atomic():
            stock_receive_po(po=po, location=default_location)
        logger.info("PO %s received by %s, stock updated", po.number, request.user.username)
        messages.success(request, f"PO {po.number} received. Stock updated.")
        return redirect("po_list")

    return render(request, "inventory/po_receive_confirm.html", {"po": po})


# ─── Stock Movements ──────────────────────────────────────────────────────────

@login_required
def stock_movement_create(request):
    clinic = _get_clinic(request.user)
    if request.method == "POST":
        form = StockMovementForm(request.POST, clinic=clinic)
        if form.is_valid():
            with transaction.atomic():
                movement = form.save(commit=False)
                movement.created_by = request.user
                movement.save()
                if movement.from_location:
                    from_stock, _ = Stock.objects.get_or_create(
                        item=movement.item, location=movement.from_location
                    )
                    from_stock.quantity -= movement.quantity
                    from_stock.save(update_fields=["quantity", "last_updated"])
                if movement.to_location:
                    to_stock, _ = Stock.objects.get_or_create(
                        item=movement.item, location=movement.to_location
                    )
                    to_stock.quantity += movement.quantity
                    to_stock.save(update_fields=["quantity", "last_updated"])
            logger.info("Stock movement recorded for item '%s' qty=%s by %s", movement.item, movement.quantity, request.user.username)
            messages.success(request, "Stock movement recorded.")
            return redirect("inventory_dashboard")
    else:
        form = StockMovementForm(clinic=clinic)

    return render(request, "inventory/movement_form.html", {"form": form})


# ─── Consumption ──────────────────────────────────────────────────────────────

@login_required
def consume_item(request):
    clinic = _get_clinic(request.user)
    if request.method == "POST":
        form = ConsumptionForm(request.POST, clinic=clinic)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                stock_consume(
                    item=cd["item"],
                    from_stock=cd["from_stock"],
                    quantity=cd["quantity"],
                    consultation=cd.get("consultation"),
                    used_by=request.user,
                    notes=cd.get("notes", ""),
                )
                logger.info("Consumption recorded: item '%s' qty=%s by %s", cd["item"], cd["quantity"], request.user.username)
                messages.success(request, "Item consumption recorded and stock updated.")
                return redirect("inventory_dashboard")
            except ValueError as exc:
                logger.warning("Consumption failed for item '%s': %s", cd.get("item"), exc)
                messages.error(request, str(exc))
    else:
        form = ConsumptionForm(clinic=clinic)

    return render(request, "inventory/consume_form.html", {"form": form})
