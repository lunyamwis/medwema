from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from prescription.models import Prescription
from prescription.serializers import PrescriptionSerializer


def _get_clinic(user):
    return user.clinics.select_related().last()


class PrescriptionViewSet(viewsets.ModelViewSet):
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["dispensed", "consultation", "item"]
    search_fields = ["consultation__patient__name", "item__name", "dosage"]
    ordering_fields = ["prescribed_at"]

    def get_queryset(self):
        return (
            Prescription.objects.filter(
                consultation__patient__clinic=_get_clinic(self.request.user)
            )
            .select_related("consultation__patient", "item", "prescribed_by")
            .order_by("-prescribed_at")
        )

    def perform_create(self, serializer):
        serializer.save(prescribed_by=self.request.user)
