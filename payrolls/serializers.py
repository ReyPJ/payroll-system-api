from rest_framework import serializers
from payrolls.models import SalaryRecord, PayPeriod


class SalaryRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    has_night_hours = serializers.SerializerMethodField()
    period_name = serializers.SerializerMethodField()

    class Meta: #type: ignore
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
            "gross_salary",
            "lunch_deduction_hours",
            "other_deductions",
            "other_deductions_description",
            "salary_to_pay",
            "paid_at",
            "sync",
            "pay_period",
            "period_name",
            "has_night_hours",
        ]

    def get_employee_name(self, obj) -> str:
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def get_has_night_hours(self, obj) -> bool:
        return obj.night_hours > 0

    def get_period_name(self, obj) -> str:
        if obj.pay_period:
            return obj.pay_period.description
        return ""


class PayPeriodSerializer(serializers.ModelSerializer):

    class Meta: #type: ignore
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
    lunch_deduction_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, default=0 #type: ignore
    )
    other_deductions = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0 #type: ignore
    )
    other_deductions_description = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )


class EmployeeNightHoursPeriodSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()


class EmployeeNightHoursSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    night_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    night_shift_factor = serializers.DecimalField(max_digits=3, decimal_places=2)
    period = EmployeeNightHoursPeriodSerializer()


class CalculateAllSalariesSerializer(serializers.Serializer):
    period_id = serializers.IntegerField(required=True)
    apply_night_factor = serializers.BooleanField(default=True)
    lunch_deduction_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, default=0 # type: ignore
    )
    other_deductions = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0 # type: ignore
    )
    other_deductions_description = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
