from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from specialists.models import (
    DebtCase,
    EquipmentItem,
    ExternalLabRequest,
    HomeVisit,
    NursingNote,
    ServiceCatalog,
    SonographyStudy,
    SpecialistProfile,
    SpecialistTask,
    SupplyInvoice,
)
from specialists.serializers import (
    DebtCaseSerializer,
    EquipmentItemSerializer,
    ExternalLabRequestSerializer,
    HomeVisitSerializer,
    NursingNoteSerializer,
    ServiceCatalogSerializer,
    SonographyStudySerializer,
    SpecialistProfileSerializer,
    SpecialistTaskSerializer,
    SupplyInvoiceSerializer,
)


def _get_clinic(user):
    return user.clinics.select_related().last()


class SpecialistProfileViewSet(viewsets.ModelViewSet):
    serializer_class = SpecialistProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["role", "is_active"]
    search_fields = ["user__first_name", "user__last_name", "email", "phone"]

    def get_queryset(self):
        return SpecialistProfile.objects.filter(clinic=_get_clinic(self.request.user)).select_related("user")


class ServiceCatalogViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceCatalogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["role", "is_active"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return ServiceCatalog.objects.filter(clinic=_get_clinic(self.request.user))


class SpecialistTaskViewSet(viewsets.ModelViewSet):
    serializer_class = SpecialistTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "role", "assigned_to", "patient"]
    search_fields = ["patient__name", "notes"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return (
            SpecialistTask.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient", "assigned_to", "service")
            .order_by("-created_at")
        )


class SonographyStudyViewSet(viewsets.ModelViewSet):
    serializer_class = SonographyStudySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["study_type", "patient"]
    search_fields = ["patient__name", "findings", "impression"]
    ordering_fields = ["performed_at"]

    def get_queryset(self):
        return (
            SonographyStudy.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient")
            .order_by("-performed_at")
        )


class NursingNoteViewSet(viewsets.ModelViewSet):
    serializer_class = NursingNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "patient"]
    search_fields = ["patient__name", "note"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return (
            NursingNote.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient", "created_by")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExternalLabRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ExternalLabRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "patient"]
    search_fields = ["patient__name", "lab_name", "subject"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return (
            ExternalLabRequest.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class HomeVisitViewSet(viewsets.ModelViewSet):
    serializer_class = HomeVisitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "patient", "clinician"]
    search_fields = ["patient__name", "address", "purpose"]
    ordering_fields = ["visit_date", "created_at"]

    def get_queryset(self):
        return (
            HomeVisit.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient", "clinician")
            .order_by("-visit_date")
        )


class SupplyInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = SupplyInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["vendor", "invoice_number"]
    ordering_fields = ["invoice_date", "created_at"]

    def get_queryset(self):
        return (
            SupplyInvoice.objects.filter(clinic=_get_clinic(self.request.user))
            .order_by("-invoice_date")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DebtCaseViewSet(viewsets.ModelViewSet):
    serializer_class = DebtCaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "patient"]
    search_fields = ["patient__name", "notes"]
    ordering_fields = ["created_at", "next_followup_at"]

    def get_queryset(self):
        return (
            DebtCase.objects.filter(clinic=_get_clinic(self.request.user))
            .select_related("patient", "bill")
            .order_by("-created_at")
        )


class EquipmentItemViewSet(viewsets.ModelViewSet):
    serializer_class = EquipmentItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "category", "notes"]

    def get_queryset(self):
        return EquipmentItem.objects.filter(clinic=_get_clinic(self.request.user)).order_by("name")
