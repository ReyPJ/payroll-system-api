from django.utils.timezone import localtime
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import AttendanceRegister
from attendance.serializers import (
    AttendanceRegisterSerializer,
    AttendanceStatsResponseSerializer,
)
from authentication.models import NFCToken
from employee.models import Employee
from timers.models import Timer


def truncate_seconds(dt):
    """Trunca segundos y microsegundos de un datetime."""
    return dt.replace(second=0, microsecond=0)


def round_early_entry(timestamp_in):
    """Redondea entradas entre 7:00-7:59 AM a las 8:00 AM."""
    if timestamp_in.hour == 7:
        return timestamp_in.replace(hour=8, minute=0, second=0, microsecond=0)
    return timestamp_in


class AttendanceMarkView(generics.CreateAPIView):
    serializer_class = AttendanceRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        nfc_token = data.get("token")

        if not nfc_token:
            return Response(
                {"error": "Token NFC es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar el token NFC
        payload = NFCToken.validate_token(nfc_token)
        if not payload:
            return Response(
                {"error": "Token NFC inválido o revocado"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Obtener el empleado del payload
        try:
            employee_id = payload.get("employee_id")
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response(
                {"error": "Empleado no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        employee_full_name = employee.get_full_name()

        # Registrar entrada con timestamp real
        AttendanceRegister.objects.create(
            employee=employee,
            method="nfc",
            timestamp_in=localtime(employee.get_current_timestamp()),
            nfc_token=nfc_token,
        )

        return Response(
            [
                {
                    "message": f"Entrada registrada exitosamente para {employee.username}"
                },
                {"employee_name": {employee_full_name}},
            ],
            status=status.HTTP_201_CREATED,
        )


class AttendanceMarkOutView(generics.UpdateAPIView):
    queryset = AttendanceRegister.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = AttendanceRegisterSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        nfc_token = data.get("token")

        if not nfc_token:
            return Response(
                {"error": "Token NFC es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar el token NFC
        payload = NFCToken.validate_token(nfc_token)
        if not payload:
            return Response(
                {"error": "Token NFC inválido o revocado"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Obtener el empleado del payload
        try:
            employee_id = payload.get("employee_id")
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response(
                {"error": "Empleado no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        attendance = (
            AttendanceRegister.objects.filter(
                employee=employee, timestamp_out__isnull=True
            )
            .order_by("-timestamp_in")
            .first()
        )

        if not attendance:
            return Response(
                {"error": "No hay registro de entrada pendiente"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee_full_name = employee.get_full_name()

        # Registrar salida con timestamp real
        attendance.timestamp_out = localtime(employee.get_current_timestamp())
        attendance.save()

        return Response(
            [
                {"message": f"Salida registrada exitosamente para {employee.username}"},
                {"employee_name": {employee_full_name}},
            ],
            status=status.HTTP_201_CREATED,
        )


class AttendanceStatsView(APIView):
    """
    Proporciona estadísticas de horas trabajadas por empleado en el período activo
    para mostrar en el frontend como gráficos, rankings, etc.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceStatsResponseSerializer

    def get(self, request):
        period_id = request.query_params.get("period_id")

        # Buscar el período especificado o el activo
        if period_id:
            from payrolls.models import PayPeriod

            try:
                pay_period = PayPeriod.objects.get(id=period_id)
            except PayPeriod.DoesNotExist:
                return Response(
                    {"error": f"No existe un período de pago con ID {period_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Usar el período activo
            from payrolls.models import PayPeriod

            pay_period = PayPeriod.objects.filter(is_closed=False).first()
            if not pay_period:
                return Response(
                    {"error": "No hay período de pago activo"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Buscar todos los empleados con registros en el período
        employees = Employee.objects.filter(
            attendanceregister__timestamp_in__date__gte=pay_period.start_date,
            attendanceregister__timestamp_in__date__lte=pay_period.end_date,
        ).distinct()

        stats = []

        for employee in employees:
            # Obtener registros completos (con entrada y salida)
            registers = AttendanceRegister.objects.filter(
                employee=employee,
                timestamp_in__date__gte=pay_period.start_date,
                timestamp_in__date__lte=pay_period.end_date,
                timestamp_out__isnull=False,
            ).order_by("timestamp_in")

            total_worked_seconds = 0
            regular_hours_seconds = 0
            night_hours_seconds = 0
            attendance_days = set()
            days_worked = 0

            for register in registers:
                timestamp_in_local = localtime(register.timestamp_in)
                timestamp_out_local = localtime(register.timestamp_out)

                # Truncar segundos (solo contar horas y minutos)
                timestamp_in_local = truncate_seconds(timestamp_in_local)
                timestamp_out_local = truncate_seconds(timestamp_out_local)

                # Redondear entradas tempranas (7:XX AM -> 8:00 AM)
                timestamp_in_local = round_early_entry(timestamp_in_local)

                # Verificar si es un día nuevo
                day_date = timestamp_in_local.date()
                if day_date not in attendance_days:
                    attendance_days.add(day_date)
                    days_worked += 1

                # Calcular tiempo trabajado en segundos (ya sin segundos/microsegundos)
                worked_time = timestamp_out_local - timestamp_in_local
                # Truncar a minutos completos
                worked_seconds = int(worked_time.total_seconds() // 60) * 60
                total_worked_seconds += worked_seconds

                # Verificar si es turno nocturno o diurno
                is_night = False

                # Verificar si tiene un timer asignado para ese día
                day_of_week = timestamp_in_local.weekday()
                timer = Timer.objects.filter(
                    employee=employee, day=day_of_week, is_active=True
                ).first()

                if timer and timer.is_night_shift:
                    is_night = True
                # Verificar por rango de horas (noche: 10pm a 6am)
                elif timestamp_in_local.hour >= 22 or timestamp_in_local.hour < 6:
                    is_night = True

                # Determinar tipo de horas (regulares o nocturnas)
                if is_night:
                    night_hours_seconds += worked_seconds
                else:
                    regular_hours_seconds += worked_seconds

            # Convertir segundos a horas
            total_hours = round(total_worked_seconds / 3600, 2)
            regular_hours = round(regular_hours_seconds / 3600, 2)
            night_hours = round(night_hours_seconds / 3600, 2)
            # No calculamos horas extras, ya que se calculan a nivel de planilla después de 96 horas quincenales

            stats.append(
                {
                    "employee_id": employee.id,  # type: ignore
                    "employee_name": employee.get_full_name(),
                    "username": employee.username,
                    "days_worked": days_worked,
                    "total_hours": total_hours,
                    "regular_hours": regular_hours,
                    "night_hours": night_hours,
                    "target_biweekly_hours": float(employee.biweekly_hours),
                    "hourly_rate": float(employee.salary_hour),
                }
            )

        # Ordenar por total de horas trabajadas (descendente)
        stats = sorted(stats, key=lambda x: x["total_hours"], reverse=True)

        # Usar los serializers para validar y serializar los datos
        data = {
            "pay_period": {
                "id": pay_period.id,  # type: ignore
                "id": pay_period.id,  # type: ignore
                "description": pay_period.description,
                "start_date": pay_period.start_date,
                "end_date": pay_period.end_date,
                "is_closed": pay_period.is_closed,
            },
            "stats": stats,
        }

        serializer = AttendanceStatsResponseSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)
