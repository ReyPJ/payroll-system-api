from rest_framework import serializers
from payrolls.models import SalaryRecord, PayPeriod
from employee.models import Employee  # noqa


class SalaryRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    has_night_hours = serializers.SerializerMethodField()

    class Meta:
        model = SalaryRecord
        fields = [
            "id",
            "employee",
            "employee_name",
            "total_hours",
            "regular_hours",
            "night_hours",
            "extra_hours",
            "night_shift_factor_applied",
            "salary_to_pay",
            "paid_at",
            "sync",
            "pay_period",
            "has_night_hours",
        ]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def get_has_night_hours(self, obj):
        return obj.night_hours > 0


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


class SalaryCalculationSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    apply_night_factor = serializers.BooleanField(default=False)
    period_id = serializers.IntegerField(required=False)
