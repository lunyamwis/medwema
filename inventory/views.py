# inventory/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Item, Stock, StockMovement, PurchaseOrder, PurchaseOrderLine, StockMovement, Location, ItemCategory, Supplier, ConsumptionRecord
from .forms import PurchaseOrderForm, PurchaseOrderLineFormset, StockMovementForm, ConsumptionForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import ItemSerializer, StockSerializer, ConsumptionSerializer

class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.all().order_by('name')
    serializer_class = ItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__id']
    search_fields = ['name','sku','barcode']
    ordering_fields = ['name','reorder_level']

class StockViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Stock.objects.select_related('item','location').all()
    serializer_class = StockSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['item__name','location__name']

class ConsumptionViewSet(viewsets.ModelViewSet):
    queryset = ConsumptionRecord.objects.select_related('item','from_stock','consultation').all()
    serializer_class = ConsumptionSerializer

    def perform_create(self, serializer):
        cr = serializer.save(used_by=self.request.user)
        # update stock levels and create StockMovement
        if cr.from_stock:
            stock = cr.from_stock
            stock.quantity -= cr.quantity
            stock.save()
            StockMovement.objects.create(
                item=cr.item,
                quantity=cr.quantity,
                from_location=stock.location,
                to_location=None,
                movement_type='OUT',
                reference=f'CONSULT-{cr.consultation.id if cr.consultation else ""}',
                created_by=self.request.user
            )


@login_required
def dashboard(request):
    # simple dashboard
    low_stock_items = [i for i in Item.objects.all() if i.total_stock() <= i.reorder_level]
    recent_movements = StockMovement.objects.select_related('item','from_location','to_location').order_by('-created_at')[:20]
    context = {
        'low_stock_items': low_stock_items,
        'recent_movements': recent_movements,
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def item_list(request):
    qs = Item.objects.all()
    q = request.GET.get('q')
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(sku__icontains=q)
    return render(request, 'inventory/item_list.html', {'items': qs})

@login_required
def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    stocks = item.stocks.select_related('location')
    movements = item.movements.select_related('from_location','to_location','created_by').all()
    return render(request, 'inventory/item_detail.html', {'item': item, 'stocks': stocks, 'movements': movements})

@login_required
def create_po(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderLineFormset(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                po = form.save(commit=False)
                po.created_by = request.user
                po.save()
                formset.instance = po
                formset.save()
            messages.success(request, "Purchase order created.")
            return redirect('po_detail', pk=po.pk)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderLineFormset()
    return render(request, 'inventory/po_form.html', {'form': form, 'formset': formset})

@login_required
def receive_po(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        # mark received and create Stock + StockMovement entries
        with transaction.atomic():
            for line in po.lines.all():
                # create/update stock at default location (e.g., Main Store)
                default_loc, _ = Location.objects.get_or_create(name='Main Store')
                stock, _ = Stock.objects.get_or_create(item=line.item, location=default_loc)
                stock.quantity += line.quantity
                stock.save()
                StockMovement.objects.create(
                    item=line.item,
                    quantity=line.quantity,
                    from_location=None,
                    to_location=default_loc,
                    movement_type='IN',
                    reference=po.number,
                    created_by=request.user
                )
            po.status = 'RECEIVED'
            po.save()
        messages.success(request, 'PO received and stock updated.')
        return redirect('po_detail', pk=po.pk)
    return render(request, 'inventory/po_receive_confirm.html', {'po': po})

@login_required
def stock_movement_create(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.created_by = request.user
            movement.save()
            # update stock levels
            if movement.from_location:
                from_stock, _ = Stock.objects.get_or_create(item=movement.item, location=movement.from_location)
                from_stock.quantity -= movement.quantity
                from_stock.save()
            if movement.to_location:
                to_stock, _ = Stock.objects.get_or_create(item=movement.item, location=movement.to_location)
                to_stock.quantity += movement.quantity
                to_stock.save()
            messages.success(request, 'Stock movement recorded.')
            return redirect('movement_list')
    else:
        form = StockMovementForm()
    return render(request, 'inventory/movement_form.html', {'form': form})

@login_required
def consume_item(request):
    if request.method == 'POST':
        form = ConsumptionForm(request.POST)
        if form.is_valid():
            cr = form.save(commit=False)
            cr.used_by = request.user
            cr.save()
            # subtract from stock
            stock = cr.from_stock
            stock.quantity -= cr.quantity
            stock.save()
            StockMovement.objects.create(
                item=cr.item,
                quantity=cr.quantity,
                from_location=stock.location,
                to_location=None,
                movement_type='OUT',
                reference=f'CONSULT-{cr.consultation.id}' if cr.consultation else None,
                created_by=request.user
            )
            messages.success(request, 'Item consumed and stock updated.')
            return redirect('inventory_dashboard')
    else:
        form = ConsumptionForm()
    return render(request, 'inventory/consume_form.html', {'form': form})


@login_required
def po_list(request):
    query = request.GET.get("q", "")
    po_list = PurchaseOrder.objects.all().select_related("supplier")

    if query:
        po_list = po_list.filter(
            Q(supplier__name__icontains=query) |
            Q(po_number__icontains=query)
        )

    paginator = Paginator(po_list.order_by("-created_at"), 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "query": query,
        "is_paginated": page_obj.has_other_pages(),
    }
    return render(request, "inventory/po_list.html", context)
