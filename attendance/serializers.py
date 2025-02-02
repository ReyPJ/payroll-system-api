from rest_framework import serializers
from attendance.models import AttendanceRegister


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
        ]
        read_only_fields = ["sync", "timestamp_in", "timestamp_out"]

    def get_employee_name(self, obj) -> str:
        return obj.employee.get_full_name()
