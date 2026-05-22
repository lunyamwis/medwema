from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from billing.models import Bill, Payment
from billing.serializers import BillSerializer, PaymentSerializer


def _get_clinic(user):
    return user.clinics.select_related().last()


class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_paid", "patient"]
    search_fields = ["patient__name", "notes"]
    ordering_fields = ["created_at", "total_amount"]

    def get_queryset(self):
        return (
            Bill.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient", "consultation")
            .prefetch_related("items")
            .order_by("-created_at")
        )


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "payment_method"]
    search_fields = ["bill__patient__name", "reference", "receipt_number"]
    ordering_fields = ["paid_at", "amount"]

    def get_queryset(self):
        return (
            Payment.objects.filter(bill__clinic=_get_clinic(self.request.user))
            .select_related("bill__patient")
            .order_by("-paid_at")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
