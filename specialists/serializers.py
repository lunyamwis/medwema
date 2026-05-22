from __future__ import annotations

from rest_framework import serializers

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


class SpecialistProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = ["id", "user", "username", "full_name", "role", "phone", "email", "is_active"]


class ServiceCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCatalog
        fields = ["id", "name", "role", "description", "price", "is_active"]


class SpecialistTaskSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.get_full_name", read_only=True, default=None)
    service_name = serializers.CharField(source="service.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SpecialistTask
        fields = [
            "id", "patient", "patient_name", "consultation", "assigned_to", "assigned_to_name",
            "role", "service", "service_name", "notes", "status", "status_display",
            "bill", "created_at", "started_at", "completed_at",
        ]


class SonographyStudySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)

    class Meta:
        model = SonographyStudy
        fields = [
            "id", "patient", "patient_name", "consultation", "task",
            "study_type", "indication", "findings", "impression",
            "report_file", "performed_by", "performed_at",
        ]


class NursingNoteSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = NursingNote
        fields = [
            "id", "patient", "patient_name", "consultation", "task",
            "category", "note", "vitals_snapshot", "created_by", "created_by_name", "created_at",
        ]


class ExternalLabRequestSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)

    class Meta:
        model = ExternalLabRequest
        fields = [
            "id", "patient", "patient_name", "consultation",
            "lab_name", "lab_email", "subject", "message",
            "status", "created_by", "created_at", "sent_at",
        ]
        read_only_fields = ["created_by", "created_at"]


class HomeVisitSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    clinician_name = serializers.CharField(source="clinician.get_full_name", read_only=True, default=None)

    class Meta:
        model = HomeVisit
        fields = [
            "id", "patient", "patient_name", "consultation",
            "visit_date", "address", "purpose", "clinician", "clinician_name",
            "status", "notes", "created_at",
        ]


class SupplyInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplyInvoice
        fields = [
            "id", "vendor", "invoice_number", "invoice_date",
            "total_amount", "attachment", "created_by", "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]


class DebtCaseSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DebtCase
        fields = [
            "id", "bill", "patient", "patient_name",
            "status", "status_display", "next_followup_at",
            "notes", "created_at",
        ]


class EquipmentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentItem
        fields = ["id", "name", "category", "qty_available", "reorder_level", "notes"]
