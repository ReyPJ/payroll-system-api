from rest_framework import generics, permissions
from rest_framework.response import Response
from timers.models import Timer
from timers.serializers import TimerSeriealizer


class TimerListCreateView(generics.ListCreateAPIView):
    serializer_class = TimerSeriealizer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Timer.objects.select_related("employee")

    def list(self, request, *args, **kwargs):
        timers = self.get_queryset()
        # Agrupamos los timers por empleado
        grouped_timers = {}
        for timer in timers:
            employee_id = timer.employee.id
            if employee_id not in grouped_timers:
                grouped_timers[employee_id] = {
                    "employee": timer.employee.id,  # Asumimos que el campo `username` existe
                    "timers": [],
                }
            grouped_timers[employee_id]["timers"].append(TimerSeriealizer(timer).data)

        # Convertimos el diccionario a una lista para retornarlo
        response_data = list(grouped_timers.values())

        return Response(response_data)


class TimerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TimerSeriealizer
    queryset = Timer.objects.all()
    permission_classes = [permissions.IsAuthenticated]


class TimerByEmployeeView(generics.ListAPIView):
    serializer_class = TimerSeriealizer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employee_id = self.kwargs["employee_id"]
        return Timer.objects.filter(employee_id=employee_id)

    def list(self, request, *args, **kwargs):
        timers = self.get_queryset()

        serializer = self.get_serializer(timers, many=True)
        return Response(serializer.data)
