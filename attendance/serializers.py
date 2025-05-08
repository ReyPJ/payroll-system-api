from rest_framework import serializers
from attendance.models import AttendanceRegister, AttendanceDetail


class AttendanceRegisterSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRegister
        fields = [
            "id",
            "employee",
            "employee_name",
            "timestamp_in",
            "timestamp_out",
            "method",
            "sync",
            "hash",
            "unique_pin",
            "qr_code",
        ]
        read_only_fields = ["sync", "timestamp_in", "timestamp_out"]
        extra_kwargs = {"employee": {"read_only": True}}  # Si aún lo incluyes

    def get_employee_name(self, obj) -> str:
        return obj.employee.get_full_name()


class AttendanceDetailSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceDetail
        fields = [
            "id",
            "employee",
            "employee_name",
            "pay_period",
            "work_date",
            "formatted_date",
            "time_in",
            "time_out",
            "regular_hours",
            "night_hours",
            "extra_hours",
            "lunch_deduction",
        ]

    def get_employee_name(self, obj):
        return obj.employee.get_full_name()

    def get_formatted_date(self, obj):
        return obj.work_date.strftime("%d/%m/%Y")
