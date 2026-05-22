from __future__ import annotations

from rest_framework import serializers

from prescription.models import Prescription


class PrescriptionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    patient_name = serializers.CharField(source="consultation.patient.name", read_only=True)
    prescribed_by_name = serializers.CharField(source="prescribed_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = Prescription
        fields = [
            "id", "consultation", "patient_name", "item", "item_name",
            "quantity", "dosage", "frequency", "duration", "instructions",
            "dispensed", "prescribed_by", "prescribed_by_name",
            "dispensed_by", "prescribed_at",
        ]
        read_only_fields = ["prescribed_by", "prescribed_at"]
