from __future__ import annotations

from rest_framework import serializers

from patient.models import Consultation, Doctor, Patient, Queue


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ["id", "name", "specialization", "phone_number", "email"]


class PatientSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True, default=None)

    class Meta:
        model = Patient
        fields = [
            "id", "patient_number", "name", "date_of_birth", "gender", "gender_display",
            "blood_group", "phone_number", "email", "address",
            "doctor", "doctor_name",
            "emergency_contact_name", "emergency_contact_phone",
            "is_active", "date_registered", "age",
        ]
        read_only_fields = ["patient_number", "date_registered"]

    def get_age(self, obj):
        return obj.age()


class ConsultationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True, default=None)

    class Meta:
        model = Consultation
        fields = "__all__"
        read_only_fields = ["consultation_number"]


class QueueSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Queue
        fields = [
            "id", "patient", "patient_name", "doctor", "doctor_name",
            "queue_number", "status", "status_display", "priority",
            "created_at", "started_at", "completed_at",
        ]
