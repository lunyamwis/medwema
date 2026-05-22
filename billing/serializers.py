from __future__ import annotations

from rest_framework import serializers

from billing.models import Bill, BillItem, Payment


class BillItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillItem
        fields = ["id", "description", "quantity", "unit_price", "total"]


class BillSerializer(serializers.ModelSerializer):
    items = BillItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id", "patient", "patient_name", "consultation",
            "total_amount", "discount", "net_amount",
            "is_paid", "notes", "created_at", "updated_at", "items",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="bill.patient.name", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "bill", "patient_name", "reference", "receipt_number",
            "amount", "status", "status_display",
            "payment_method", "payment_method_display",
            "paid_at", "created_by",
        ]
        read_only_fields = ["reference", "receipt_number", "created_by"]
