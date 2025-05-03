from rest_framework import serializers
from payrolls.models import SalaryRecord, PayPeriod


class SalaryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryRecord
        fields = [
            "employee",
            "total_hours",
            "extra_hours",
            "salary_to_pay",
            "paid_at",
            "sync",
            "pay_period",
        ]


class PayPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayPeriod
        fields = [
            "id",
            "start_date",
            "end_date",
            "is_closed",
            "description",
        ]
