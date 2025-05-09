from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework import serializers
from employee.models import Employee


class EmployeeSerializer(ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            "salary_hour",
            "biweekly_hours",
            "night_shift_factor",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_admin",
            "use_finger_print",
            "use_face_id",
            "fingerprint_hash",
            "face_tamplate",
            "phone",
            "unique_pin",
            "qr_code",
        ]

    def get_qr_code(self, obj):
        return obj.qr_code


class CurrentlyWorkingEmployeeSerializer(Serializer):
    """
    Serializer para los empleados que están actualmente trabajando.
    Incluye información sobre su marca de entrada activa.
    """

    id = serializers.IntegerField()
    full_name = serializers.CharField()
    username = serializers.CharField()
    timestamp_in = serializers.DateTimeField()
    method = serializers.CharField()
