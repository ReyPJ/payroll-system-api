from rest_framework import serializers
from attendance.models import AttendanceRegister, AttendanceDetail


class AttendanceRegisterSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta: #type: ignore
        model = AttendanceRegister
        fields = [
            "id",
            "employee",
            "employee_name",
            "timestamp_in",
            "timestamp_out",
            "method",
            "sync",
            "nfc_token",
        ]
        read_only_fields = ["sync", "timestamp_in", "timestamp_out"]
        extra_kwargs = {"employee": {"read_only": True}}

    def get_employee_name(self, obj) -> str:
        return obj.employee.get_full_name()


class AttendanceDetailSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()

    class Meta: #type: ignore
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

    def get_employee_name(self, obj) -> str:
        return obj.employee.get_full_name()

    def get_formatted_date(self, obj) -> str:
        return obj.work_date.strftime("%d/%m/%Y")


class AttendanceStatsEmployeeSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    employee_name = serializers.CharField()
    username = serializers.CharField()
    days_worked = serializers.IntegerField()
    total_hours = serializers.FloatField()
    regular_hours = serializers.FloatField()
    night_hours = serializers.FloatField()
    target_biweekly_hours = serializers.FloatField()
    hourly_rate = serializers.FloatField()


class AttendanceStatsResponseSerializer(serializers.Serializer):
    pay_period = serializers.DictField()
    stats = serializers.ListField()
