from rest_framework.serializers import ModelSerializer
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
        ]
