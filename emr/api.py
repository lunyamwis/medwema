from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from emr.models import Lab, LabQueue, LabResult, LabTest
from emr.serializers import (
    LabQueueSerializer,
    LabResultSerializer,
    LabSerializer,
    LabTestSerializer,
)


def _get_clinic(user):
    return user.clinics.select_related().last()


class LabViewSet(viewsets.ModelViewSet):
    serializer_class = LabSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["lab_type"]
    search_fields = ["name", "location"]

    def get_queryset(self):
        return Lab.objects.filter(clinic=_get_clinic(self.request.user)).order_by("name")


class LabTestViewSet(viewsets.ModelViewSet):
    serializer_class = LabTestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["lab", "category", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "price"]

    def get_queryset(self):
        return (
            LabTest.objects.filter(lab__clinic=_get_clinic(self.request.user))
            .select_related("lab")
            .order_by("name")
        )


class LabResultViewSet(viewsets.ModelViewSet):
    serializer_class = LabResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["lab_test", "consultation"]
    search_fields = ["consultation__patient__name", "result_name"]
    ordering_fields = ["result_date"]

    def get_queryset(self):
        return (
            LabResult.objects.filter(consultation__patient__clinic=_get_clinic(self.request.user))
            .select_related("lab_test", "consultation__patient")
            .order_by("-result_date")
        )


class LabQueueViewSet(viewsets.ModelViewSet):
    serializer_class = LabQueueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "patient", "lab_test"]
    ordering_fields = ["created_at", "queue_number"]

    def get_queryset(self):
        return (
            LabQueue.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient", "lab_test")
            .order_by("created_at")
        )
