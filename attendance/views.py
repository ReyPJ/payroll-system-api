from rest_framework import generics, permissions, status
from rest_framework.response import Response
from attendance.serializers import AttendanceRegisterSerializer
from employee.models import Employee
from attendance.models import AttendanceRegister
from django.utils.timezone import localtime
from timers.models import Timer
from rest_framework.views import APIView


class AttendanceMarkView(generics.CreateAPIView):
    serializer_class = AttendanceRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        method = data.get("method")
        hash_value = data.get("hash")
        unique_pin = data.get("unique_pin")
        qr_code = data.get("qr_code")

        if (
            not method
            or (method != "pin" and not hash_value)
            and (method == "pin" and not unique_pin)
            and (method == "qr_code" and not qr_code)
        ):
            return Response(
                {"error": "Método e identificador son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar empleado según método de autenticación
        if method == "fingerprint":
            employee = Employee.objects.filter(fingerprint_hash=hash_value).first()
        elif method == "faceId":
            employee = Employee.objects.filter(face_tamplate=hash_value).first()
        elif method == "pin":
            employee = Employee.objects.filter(
                is_admin=False, unique_pin=unique_pin
            ).first()
        elif method == "qr_code":
            employee = Employee.objects.filter(qr_code=qr_code).first()
        else:
            return Response(
                {"error": "Método no válido"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not employee:
            return Response(
                {"error": "Empleado no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        employee_full_name = employee.get_full_name()

        # Registrar entrada con timestamp real
        AttendanceRegister.objects.create(
            employee=employee,
            method=method,
            timestamp_in=localtime(employee.get_current_timestamp()),
            hash=hash_value if method != "pin" else "",
            unique_pin=unique_pin if method == "pin" else None,
            qr_code=qr_code if method == "qr_code" else None,
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
        method = data.get("method")
        hash_value = data.get("hash")
        unique_pin = data.get("unique_pin")

        if (
            not method
            or (method != "pin" and not hash_value)
            and (method == "pin" and not unique_pin)
        ):
            return Response(
                {"error": "Método e identificador son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar empleado
        if method == "fingerprint":
            employee = Employee.objects.filter(fingerprint_hash=hash_value).first()
        elif method == "faceId":
            employee = Employee.objects.filter(face_tamplate=hash_value).first()
        elif method == "pin":
            employee = Employee.objects.filter(
                is_admin=False, unique_pin=unique_pin
            ).first()
        else:
            return Response(
                {"error": "Método no válido"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not employee:
            return Response(
                {"error": "Empleado no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        # Buscar registro de entrada pendiente
        attendance = AttendanceRegister.objects.filter(
            employee=employee, timestamp_out__isnull=True
        ).first()

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

    permission_classes = [permissions.AllowAny]

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

                # Verificar si es un día nuevo
                day_date = timestamp_in_local.date()
                if day_date not in attendance_days:
                    attendance_days.add(day_date)
                    days_worked += 1

                # Calcular tiempo trabajado en segundos
                worked_time = timestamp_out_local - timestamp_in_local
                worked_seconds = worked_time.total_seconds()
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
                    "employee_id": employee.id,
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

        return Response(
            {
                "pay_period": {
                    "id": pay_period.id,
                    "description": pay_period.description,
                    "start_date": pay_period.start_date,
                    "end_date": pay_period.end_date,
                    "is_closed": pay_period.is_closed,
                },
                "stats": stats,
            }
        )
