from rest_framework import serializers
from timers.models import Timer


class TimerSeriealizer(serializers.ModelSerializer):
    day_display = serializers.SerializerMethodField()
    employee_username = serializers.CharField(
        source="employee.username", read_only=True
    )

    class Meta:
        model = Timer
        fields = [
            "id",
            "employee",
            "employee_username",
            "day",
            "timeIn",
            "day_display",
            "expected_hours",
            "is_active",
        ]

    def get_day_display(self, obj) -> str:
        days = [
            "Domingo",
            "Lunes",
            "Martes",
            "Miercoles",
            "Jueves",
            "Viernes",
            "Sabado",
        ]
        return days[obj.day]

    def validate(self, data):
        # Podríamos agregar validaciones adicionales para expected_hours aquí
        if data.get("expected_hours", 0) <= 0:
            raise serializers.ValidationError(
                "Las horas esperadas deben ser un valor positivo"
            )
        return data
