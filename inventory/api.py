from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from inventory.models import (
    ItemCategory,
    Location,
    PurchaseOrder,
    StockMovement,
    Supplier,
)
from inventory.serializers import (
    ItemCategorySerializer,
    LocationSerializer,
    PurchaseOrderSerializer,
    StockMovementSerializer,
    SupplierSerializer,
)


def _get_clinic(user):
    return user.clinics.select_related().last()


class ItemCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ItemCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        return ItemCategory.objects.filter(clinic=_get_clinic(self.request.user)).order_by("name")


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "contact", "email"]

    def get_queryset(self):
        return Supplier.objects.filter(clinic=_get_clinic(self.request.user)).order_by("name")


class LocationViewSet(viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        return Location.objects.filter(clinic=_get_clinic(self.request.user)).order_by("name")


class StockMovementViewSet(viewsets.ModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["movement_type", "item"]
    search_fields = ["item__name", "reference", "notes"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return (
            StockMovement.objects.filter(item__clinic=_get_clinic(self.request.user))
            .select_related("item", "from_location", "to_location", "created_by")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "supplier"]
    search_fields = ["number", "supplier__name", "notes"]
    ordering_fields = ["created_at", "expected_date"]

    def get_queryset(self):
        return (
            PurchaseOrder.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("supplier")
            .prefetch_related("lines__item")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
