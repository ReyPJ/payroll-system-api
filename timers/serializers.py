from rest_framework import serializers
from timers.models import Timer


class TimerSeriealizer(serializers.ModelSerializer):
    day_display = serializers.SerializerMethodField()

    class Meta:
        model = Timer
        fields = ["id", "employee", "day", "timeIn", "timeOut", "day_display"]

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
        if data["timeOut"] <= data["timeIn"]:
            raise serializers.ValidationError(
                "La hora de salida debe ser despues de la hora de entrada"
            )
        return data
