from __future__ import annotations

from rest_framework import serializers

from emr.models import Lab, LabQueue, LabResult, LabTest


class LabSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lab
        fields = ["id", "name", "location", "lab_type", "created_at"]


class LabTestSerializer(serializers.ModelSerializer):
    lab_name = serializers.CharField(source="lab.name", read_only=True)

    class Meta:
        model = LabTest
        fields = [
            "id", "lab", "lab_name", "name", "category",
            "unit", "reference_min", "reference_max", "reference_text",
            "price", "description", "is_active", "created_at",
        ]


class LabResultSerializer(serializers.ModelSerializer):
    lab_test_name = serializers.CharField(source="lab_test.name", read_only=True, default=None)
    patient_name = serializers.CharField(source="consultation.patient.name", read_only=True)

    class Meta:
        model = LabResult
        fields = [
            "id", "lab_test", "lab_test_name", "consultation", "patient_name",
            "result_name", "result_value", "result_date",
        ]


class LabQueueSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    lab_test_name = serializers.CharField(source="lab_test.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LabQueue
        fields = [
            "id", "patient", "patient_name", "lab_test", "lab_test_name",
            "consultation", "queue_number", "status", "status_display",
            "created_at", "started_at", "completed_at",
        ]
