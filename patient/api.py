from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from patient.models import Consultation, Doctor, Patient, Queue
from patient.serializers import (
    ConsultationSerializer,
    DoctorSerializer,
    PatientSerializer,
    QueueSerializer,
)


def _get_clinic(user):
    return user.clinics.select_related().last()


class DoctorViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "specialization", "email"]
    ordering_fields = ["name"]

    def get_queryset(self):
        return Doctor.objects.filter(clinic=_get_clinic(self.request.user)).order_by("name")


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["gender", "is_active", "doctor"]
    search_fields = ["name", "phone_number", "patient_number", "email"]
    ordering_fields = ["name", "date_registered"]

    def get_queryset(self):
        return (
            Patient.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("doctor")
            .order_by("name")
        )


class ConsultationViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "doctor", "patient"]
    search_fields = ["patient__name", "diagnosis", "chief_complaints"]
    ordering_fields = ["date"]

    def get_queryset(self):
        return (
            Consultation.objects.filter(patient__clinic=_get_clinic(self.request.user))
            .select_related("patient", "doctor")
            .order_by("-date")
        )


class QueueViewSet(viewsets.ModelViewSet):
    serializer_class = QueueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "doctor", "patient", "priority"]
    ordering_fields = ["created_at", "queue_number"]

    def get_queryset(self):
        return (
            Queue.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient", "doctor")
            .order_by("created_at")
        )
