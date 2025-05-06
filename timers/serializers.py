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

    def validate(self, data):
        if data.get("timeOut") <= data.get("timeIn"):
            raise serializers.ValidationError(
                "La hora de salida debe ser después de la hora de entrada"
            )
        return data
