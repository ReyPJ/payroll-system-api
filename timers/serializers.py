from rest_framework import serializers
from timers.models import Timer


class TimerSeriealizer(serializers.ModelSerializer):
    day_display = serializers.SerializerMethodField()
    employee_username = serializers.CharField(
        source="employee.username", read_only=True
    )

    class Meta: #type: ignore
        model = Timer
        fields = [
            "id",
            "employee",
            "employee_username",
            "day",
            "timeIn",
            "timeOut",
            "day_display",
            "is_active",
            "is_night_shift",
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

    def validate(self, data): #type: ignore
        # Para turnos nocturnos permitimos que la hora de salida sea menor que la de entrada
        if not data.get("is_night_shift") and data.get("timeOut") <= data.get("timeIn"):
            raise serializers.ValidationError(
                "La hora de salida debe ser después de la hora de entrada"
            )
        return data
