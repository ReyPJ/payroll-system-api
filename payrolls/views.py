from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status
from rest_framework.views import APIView
from employee.models import Employee
from payrolls.services.calculate_payroll import calculate_pay_to_go, calculate_night_hours
from payrolls.models import SalaryRecord, PayPeriod
from payrolls.serializers import (
    SalaryRecordSerializer,
    PayPeriodSerializer,
    SalaryCalculationSerializer,
    EmployeeNightHoursSerializer,
    CalculateAllSalariesSerializer,
)
from datetime import date, timedelta
from attendance.models import AttendanceRegister
from django.utils.timezone import localtime
from timers.models import Timer
from decimal import Decimal


class CalculateSalary(generics.CreateAPIView):
    serializer_class = SalaryCalculationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee_id = serializer.validated_data["employee_id"]
        apply_night_factor = serializer.validated_data.get("apply_night_factor", False)
        period_id = serializer.validated_data.get("period_id", None)
        other_deductions = serializer.validated_data.get("other_deductions", 0)
        other_deductions_description = serializer.validated_data.get(
            "other_deductions_description", ""
        )

        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            raise NotFound(detail="Empleado no encontrado")

        # Si se proporciona period_id, usar ese período específico
        if period_id:
            try:
                pay_period = PayPeriod.objects.get(id=period_id)
            except PayPeriod.DoesNotExist:
                return Response(
                    {"error": f"No existe un período de pago con ID {period_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Verificar que haya un periodo activo
            pay_period = PayPeriod.objects.filter(is_closed=False).first()
            if not pay_period:
                return Response(
                    {"error": "No hay período de pago activo"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # VALIDACIÓN: Advertir si se está calculando antes del fin del período
        today = date.today()
        warnings = []

        if today < pay_period.end_date:
            days_remaining = (pay_period.end_date - today).days
            warnings.append({
                "type": "early_calculation",
                "message": f"⚠️ ADVERTENCIA: Estás calculando el salario {days_remaining} día(s) antes del fin del período ({pay_period.end_date.strftime('%d/%m/%Y')})",
                "details": "Si el empleado sigue trabajando, tendrás que recalcular usando el comando 'reset_attendance_paid_status'",
                "days_remaining": days_remaining,
                "period_end_date": pay_period.end_date.isoformat(),
            })

        # Verificar si ya existe un SalaryRecord para este empleado y período
        salary_record = SalaryRecord.objects.filter(
            employee=employee, pay_period=pay_period
        ).first()

        # VALIDACIÓN: Advertir si ya existe un cálculo previo
        if salary_record:
            paid_attendance_count = AttendanceRegister.objects.filter(
                employee=employee,
                pay_period=pay_period,
                paid=True,
            ).count()

            warnings.append({
                "type": "recalculation",
                "message": f"⚠️ Ya existe un cálculo previo para este empleado en este período",
                "details": f"Tienes {paid_attendance_count} registros de asistencia ya marcados como pagados. El cálculo se actualizará pero solo con registros nuevos no pagados.",
                "previous_calculation_date": salary_record.paid_at.isoformat(),
                "previous_total_hours": str(salary_record.total_hours),
                "previous_salary": str(salary_record.salary_to_pay),
            })

        # Llamamos a la función que calcula el salario con el period_id si se proporcionó
        salary_data = calculate_pay_to_go(
            employee,
            apply_night_factor,
            period_id,
            other_deductions,
            other_deductions_description,
        )

        if "error" in salary_data:
            return Response(
                {"error": salary_data["error"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if salary_record:
            # Si ya existe, actualizamos los campos
            salary_record.total_hours = salary_data["total_hours"]
            salary_record.regular_hours = salary_data["regular_hours"]
            salary_record.night_hours = salary_data["night_hours"]
            salary_record.extra_hours = salary_data["extra_hours"]
            salary_record.night_shift_factor_applied = salary_data[
                "night_shift_factor_applied"
            ]
            salary_record.gross_salary = salary_data["gross_salary"]
            salary_record.lunch_deduction_hours = salary_data["lunch_deduction_hours"]
            salary_record.other_deductions = salary_data["other_deductions"]
            salary_record.other_deductions_description = salary_data[
                "other_deductions_description"
            ]
            salary_record.salary_to_pay = salary_data["salary_to_pay"]
            salary_record.save()
        else:
            # Si no existe, lo creamos
            salary_record = SalaryRecord.objects.create(
                pay_period=pay_period,
                employee=employee,
                total_hours=salary_data["total_hours"],
                regular_hours=salary_data["regular_hours"],
                night_hours=salary_data["night_hours"],
                extra_hours=salary_data["extra_hours"],
                night_shift_factor_applied=salary_data["night_shift_factor_applied"],
                gross_salary=salary_data["gross_salary"],
                lunch_deduction_hours=salary_data["lunch_deduction_hours"],
                other_deductions=salary_data["other_deductions"],
                other_deductions_description=salary_data[
                    "other_deductions_description"
                ],
                salary_to_pay=salary_data["salary_to_pay"],
            )

        serializer = SalaryRecordSerializer(salary_record)

        # Construir respuesta con advertencias si existen
        response_data = serializer.data
        if warnings:
            response_data = {
                "salary_record": serializer.data,
                "warnings": warnings,
            }

        return Response(response_data, status=status.HTTP_201_CREATED)


class ManagePayPeriodView(APIView):
    """
    Vista para manejar los períodos de pago:
    - Obtener períodos de pago (activos/cerrados)
    - Cerrar el período actual
    - Crear un nuevo período
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PayPeriodSerializer

    def get(self, request):
        """
        Obtiene información sobre los períodos de pago:
        - Si se proporciona period_id, devuelve ese período específico
        - Si is_active=true, devuelve solo el período activo (no cerrado)
        - De lo contrario, devuelve todos los períodos
        """
        period_id = request.query_params.get("period_id", None)
        is_active = request.query_params.get("is_active", "").lower() == "true"

        # Obtener un período específico por ID
        if period_id:
            try:
                period = PayPeriod.objects.get(id=period_id)
                serializer = self.serializer_class(period)
                return Response(serializer.data)
            except PayPeriod.DoesNotExist:
                return Response(
                    {"error": f"No existe un período de pago con ID {period_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Obtener solo el período activo
        if is_active:
            period = PayPeriod.objects.filter(is_closed=False).first()
            if not period:
                return Response(
                    {"error": "No hay un período de pago activo"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = self.serializer_class(period)
            return Response(serializer.data)

        # Obtener todos los períodos
        periods = PayPeriod.objects.all().order_by("-start_date")
        serializer = self.serializer_class(periods, many=True)
        return Response(serializer.data)

    def post(self, request):
        action = request.data.get("action", "")

        # Validar acción
        if action not in ["close_current", "create_new", "close_and_create_new"]:
            return Response(
                {"error": "Acción no válida. Use 'close_current', 'create_new' o 'close_and_create_new'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cerrar período actual
        if action == "close_current":
            current_period = PayPeriod.objects.filter(is_closed=False).first()
            if not current_period:
                return Response(
                    {"error": "No hay un período de pago abierto"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            current_period.is_closed = True
            current_period.save()

            serializer = PayPeriodSerializer(current_period)
            return Response(
                {"message": "Período cerrado correctamente", "period": serializer.data}
            )

        # Crear nuevo período
        elif action == "create_new":
            # Verificar que no haya períodos abiertos
            if PayPeriod.objects.filter(is_closed=False).exists():
                return Response(
                    {"error": "Ya existe un período abierto. Ciérrelo primero."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            today = date.today()
            end_date = today + timedelta(days=15)  # Por defecto 15 días

            # Personalizar fechas si se proporcionan
            start_date = request.data.get("start_date", today)
            if isinstance(start_date, str):
                from datetime import datetime

                try:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                except ValueError:
                    start_date = datetime.strptime(start_date, "%d/%m/%Y").date()
            if "end_date" in request.data:
                end_date = request.data.get("end_date")
                if isinstance(end_date, str):
                    from datetime import datetime

                    try:
                        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                    except ValueError:
                        end_date = datetime.strptime(end_date, "%d/%m/%Y").date()

            new_period = PayPeriod.objects.create(
                start_date=start_date, end_date=end_date, is_closed=False
            )

            serializer = PayPeriodSerializer(new_period)
            return Response(
                {"message": "Nuevo período creado", "period": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        # Cerrar período actual, crear uno nuevo Y migrar entradas actuales
        elif action == "close_and_create_new":
            from django.db import transaction
            from payrolls.services.period_migration import migrate_current_shifts_to_new_period

            # Verificar que haya un período abierto
            current_period = PayPeriod.objects.filter(is_closed=False).first()
            if not current_period:
                return Response(
                    {"error": "No hay un período de pago abierto para cerrar"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Preparar fechas del nuevo período
            today = date.today()
            end_date = today + timedelta(days=15)  # Por defecto 15 días

            # Personalizar fechas si se proporcionan
            start_date = request.data.get("start_date", today)
            if isinstance(start_date, str):
                from datetime import datetime

                try:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                except ValueError:
                    start_date = datetime.strptime(start_date, "%d/%m/%Y").date()

            if "end_date" in request.data:
                end_date = request.data.get("end_date")
                if isinstance(end_date, str):
                    from datetime import datetime

                    try:
                        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                    except ValueError:
                        end_date = datetime.strptime(end_date, "%d/%m/%Y").date()

            # Usar transacción para asegurar atomicidad
            with transaction.atomic():
                # 1. Crear el nuevo período primero
                new_period = PayPeriod.objects.create(
                    start_date=start_date, end_date=end_date, is_closed=False
                )

                # 2. Migrar las entradas actuales al nuevo período
                migration_result = migrate_current_shifts_to_new_period(
                    current_period, new_period
                )

                # 3. Cerrar el período actual
                current_period.is_closed = True
                current_period.save()

            # Preparar respuesta
            closed_period_serializer = PayPeriodSerializer(current_period)
            new_period_serializer = PayPeriodSerializer(new_period)

            return Response(
                {
                    "message": "Período cerrado, nuevo período creado y entradas actuales migradas exitosamente",
                    "closed_period": closed_period_serializer.data,
                    "new_period": new_period_serializer.data,
                    "migration": {
                        "migrated_count": migration_result["migrated_count"],
                        "migrated_employees": [
                            {
                                "employee_id": record["employee_id"],
                                "employee_username": record["employee_username"],
                                "timestamp_in": record["timestamp_in"],
                            }
                            for record in migration_result["migrated_records"]
                        ],
                        "message": migration_result["message"],
                    },
                },
                status=status.HTTP_201_CREATED,
            )


class ListEmployeesWithNightHours(APIView):
    """
    Lista los empleados que tienen horas nocturnas en el período actual o en el especificado
    para que el admin pueda decidir a quiénes aplicar el factor de pago nocturno
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeNightHoursSerializer

    def get(self, request):
        # Obtener period_id de los parámetros de la consulta
        period_id = request.query_params.get("period_id", None)

        if period_id:
            try:
                pay_period = PayPeriod.objects.get(id=period_id)
            except PayPeriod.DoesNotExist:
                return Response(
                    {"error": f"No existe un período de pago con ID {period_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Verificar que haya un periodo activo
            pay_period = PayPeriod.objects.filter(is_closed=False).first()
            if not pay_period:
                return Response(
                    {"error": "No hay período de pago activo"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        employees_with_night_hours = []

        # Obtener todos los empleados que tienen registros en el período seleccionado
        employees = Employee.objects.filter(
            attendanceregister__timestamp_in__date__gte=pay_period.start_date,
            attendanceregister__timestamp_in__date__lte=pay_period.end_date,
            attendanceregister__paid=False,
        ).distinct()

        for employee in employees:
            # Obtener todos los registros del empleado en el período seleccionado
            registers = AttendanceRegister.objects.filter(
                employee=employee,
                timestamp_in__date__gte=pay_period.start_date,
                timestamp_in__date__lte=pay_period.end_date,
                paid=False,
            ).order_by("timestamp_in")

            has_night_hours = False
            total_night_hours = timedelta()

            for register in registers:
                if not register.timestamp_out:
                    continue

                timestamp_in_local = localtime(register.timestamp_in)
                timestamp_out_local = localtime(register.timestamp_out)

                # Verificar si el turno es nocturno según Timer
                day_of_week = timestamp_in_local.weekday()
                timer = Timer.objects.filter(
                    employee=employee, day=day_of_week, is_active=True
                ).first()

                # Calcular horas nocturnas REALES
                if timer and timer.is_night_shift:
                    # Si el timer está marcado como nocturno, todas las horas cuentan
                    night_hours_for_shift = timestamp_out_local - timestamp_in_local
                else:
                    # Calcular solo las horas que realmente cayeron en horario nocturno
                    night_hours_for_shift = calculate_night_hours(timestamp_in_local, timestamp_out_local)

                if night_hours_for_shift.total_seconds() > 0:
                    has_night_hours = True
                    total_night_hours += night_hours_for_shift

            if has_night_hours:
                night_hours_decimal = Decimal(
                    total_night_hours.total_seconds()
                ) / Decimal(3600)
                employees_with_night_hours.append(
                    {
                        "id": employee.id,
                        "username": employee.username,
                        "full_name": f"{employee.first_name} {employee.last_name}",
                        "night_hours": night_hours_decimal.quantize(Decimal("0.01")),
                        "night_shift_factor": employee.night_shift_factor,
                        "period": {
                            "id": pay_period.id,
                            "description": pay_period.description,
                        },
                    }
                )

        # Serializar la respuesta
        serializer = self.serializer_class(employees_with_night_hours, many=True)
        return Response(serializer.data)


class CalculateAllSalaries(APIView):
    """
    Calcula el salario de todos los empleados para un período específico
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CalculateAllSalariesSerializer

    def get(self, request):
        # Validar parámetros con el serializer
        serializer = self.serializer_class(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        period_id = serializer.validated_data["period_id"]
        apply_night_factor = serializer.validated_data.get("apply_night_factor", True)
        other_deductions = serializer.validated_data.get("other_deductions", 0)
        other_deductions_description = serializer.validated_data.get(
            "other_deductions_description", ""
        )

        try:
            pay_period = PayPeriod.objects.get(id=period_id)
        except PayPeriod.DoesNotExist:
            return Response(
                {"error": f"No existe un período de pago con ID {period_id}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # VALIDACIÓN: Advertir si se está calculando antes del fin del período
        today = date.today()
        warnings = []

        if today < pay_period.end_date:
            days_remaining = (pay_period.end_date - today).days
            warnings.append({
                "type": "early_calculation",
                "message": f"⚠️ ADVERTENCIA: Estás calculando salarios {days_remaining} día(s) antes del fin del período ({pay_period.end_date.strftime('%d/%m/%Y')})",
                "details": "Si los empleados siguen trabajando, tendrás que recalcular usando el comando 'reset_attendance_paid_status'",
                "days_remaining": days_remaining,
                "period_end_date": pay_period.end_date.isoformat(),
            })

        # Obtener empleados con registros en el período
        employees = Employee.objects.filter(
            attendanceregister__timestamp_in__date__gte=pay_period.start_date,
            attendanceregister__timestamp_in__date__lte=pay_period.end_date,
            attendanceregister__paid=False,
        ).distinct()

        if not employees.exists():
            return Response(
                {
                    "error": f"No hay empleados con registros pendientes de pago en el período {pay_period.description}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calcular salarios para cada empleado
        salary_records = []
        total_planilla = Decimal("0.0")

        for employee in employees:
            # Buscar si ya existe un SalaryRecord para este empleado y período
            salary_record = SalaryRecord.objects.filter(
                employee=employee, pay_period=pay_period
            ).first()

            # Calcular salario utilizando apply_night_factor del serializer
            salary_data = calculate_pay_to_go(
                employee,
                apply_night_factor=apply_night_factor,
                period_id=period_id,
                other_deductions=other_deductions,
                other_deductions_description=other_deductions_description,
            )

            if "error" in salary_data:
                continue

            if salary_record:
                # Si ya existe, actualizamos los campos
                salary_record.total_hours = salary_data["total_hours"]
                salary_record.regular_hours = salary_data["regular_hours"]
                salary_record.night_hours = salary_data["night_hours"]
                salary_record.extra_hours = salary_data["extra_hours"]
                salary_record.night_shift_factor_applied = salary_data[
                    "night_shift_factor_applied"
                ]
                salary_record.gross_salary = salary_data["gross_salary"]
                salary_record.lunch_deduction_hours = salary_data[
                    "lunch_deduction_hours"
                ]
                salary_record.other_deductions = salary_data["other_deductions"]
                salary_record.other_deductions_description = salary_data[
                    "other_deductions_description"
                ]
                salary_record.salary_to_pay = salary_data["salary_to_pay"]
                salary_record.save()
            else:
                # Crear registro de salario
                salary_record = SalaryRecord.objects.create(
                    pay_period=pay_period,
                    employee=employee,
                    total_hours=salary_data["total_hours"],
                    regular_hours=salary_data["regular_hours"],
                    night_hours=salary_data["night_hours"],
                    extra_hours=salary_data["extra_hours"],
                    night_shift_factor_applied=salary_data[
                        "night_shift_factor_applied"
                    ],
                    gross_salary=salary_data["gross_salary"],
                    lunch_deduction_hours=salary_data["lunch_deduction_hours"],
                    other_deductions=salary_data["other_deductions"],
                    other_deductions_description=salary_data[
                        "other_deductions_description"
                    ],
                    salary_to_pay=salary_data["salary_to_pay"],
                )

            salary_records.append(salary_record)
            total_planilla += salary_data["salary_to_pay"]

        # Serializar y devolver resultados
        serializer = SalaryRecordSerializer(salary_records, many=True)

        response_data = {
            "message": "Cálculo de planilla completado",
            "records": serializer.data,
            "total_planilla": total_planilla,
            "empleados_procesados": len(salary_records),
        }

        # Agregar advertencias si existen
        if warnings:
            response_data["warnings"] = warnings

        return Response(response_data)


class ListSalaryRecordsByPeriod(generics.ListAPIView):
    """
    Lista todos los registros de salario para un período específico
    """

    serializer_class = SalaryRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        period_id = self.request.query_params.get("period_id")
        if not period_id:
            return SalaryRecord.objects.none()

        try:
            return SalaryRecord.objects.filter(pay_period_id=period_id).select_related(
                "employee", "pay_period"
            )
        except Exception:
            return SalaryRecord.objects.none()


class SalaryRecordEmployeeDetail(generics.RetrieveAPIView):
    """
    Obtiene el detalle de un registro de salario por ID
    """

    serializer_class = SalaryRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SalaryRecord.objects.all()


class EmployeeAttendanceDetailView(generics.ListAPIView):
    """
    Obtiene los detalles de asistencia para un empleado en un período específico
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        from attendance.serializers import AttendanceDetailSerializer

        return AttendanceDetailSerializer

    def get_queryset(self):
        from attendance.models import AttendanceDetail

        employee_id = self.request.query_params.get("employee_id")
        period_id = self.request.query_params.get("period_id")

        if not employee_id or not period_id:
            return AttendanceDetail.objects.none()

        try:
            return AttendanceDetail.objects.filter(
                employee_id=employee_id, pay_period_id=period_id
            ).order_by("work_date")
        except Exception:
            return AttendanceDetail.objects.none()


class LiveAttendanceSummaryView(APIView):
    """
    Obtiene un resumen en tiempo real de las horas acumuladas en el período activo
    SIN calcular el salario ni marcar registros como pagados.

    GET /payrolls/live-summary/?period_id=5&employee_id=10
    GET /payrolls/live-summary/?period_id=5  (todos los empleados)

    Respuesta:
    {
        "period": {...},
        "employees": [
            {
                "employee_id": 10,
                "employee_username": "juan.perez",
                "total_hours": "112.5",
                "regular_hours": "96.0",
                "night_hours": "2.5",
                "extra_hours": "16.5",
                "estimated_salary": "1250.00",
                "days_worked": 14,
                "pending_checkout": 0
            }
        ]
    }
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get("period_id")
        employee_id = request.query_params.get("employee_id")

        # Si no se proporciona period_id, buscar el período activo
        if period_id:
            try:
                pay_period = PayPeriod.objects.get(id=period_id)
            except PayPeriod.DoesNotExist:
                return Response(
                    {"error": f"No existe un período de pago con ID {period_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            pay_period = PayPeriod.objects.filter(is_closed=False).first()
            if not pay_period:
                return Response(
                    {"error": "No hay período de pago activo"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Obtener empleados a procesar
        if employee_id:
            try:
                employees = [Employee.objects.get(id=employee_id)]
            except Employee.DoesNotExist:
                return Response(
                    {"error": f"No existe empleado con ID {employee_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Todos los empleados con registros en este período
            employees = Employee.objects.filter(
                attendanceregister__timestamp_in__date__gte=pay_period.start_date,
                attendanceregister__timestamp_in__date__lte=pay_period.end_date,
            ).distinct()

        employees_summary = []

        for employee in employees:
            # Obtener todos los registros (pagados y no pagados) para ver el total real
            records = AttendanceRegister.objects.filter(
                employee=employee,
                timestamp_in__date__gte=pay_period.start_date,
                timestamp_in__date__lte=pay_period.end_date,
            ).order_by("timestamp_in")

            if not records.exists():
                continue

            total_worked_hours = timedelta()
            total_night_hours = timedelta()
            pending_checkout = 0
            days_worked = set()

            for record in records:
                if not record.timestamp_out:
                    pending_checkout += 1
                    continue

                timestamp_in_local = localtime(record.timestamp_in)
                timestamp_out_local = localtime(record.timestamp_out)

                if timestamp_out_local <= timestamp_in_local:
                    continue

                worked_hours = timestamp_out_local - timestamp_in_local
                days_worked.add(timestamp_in_local.date())

                # Calcular horas nocturnas
                day_of_week = timestamp_in_local.weekday()
                timer = Timer.objects.filter(
                    employee=employee, day=day_of_week, is_active=True
                ).first()

                if timer and timer.is_night_shift:
                    night_hours_for_shift = worked_hours
                else:
                    night_hours_for_shift = calculate_night_hours(
                        timestamp_in_local, timestamp_out_local
                    )

                total_night_hours += night_hours_for_shift
                total_worked_hours += worked_hours

            # Convertir a decimal
            total_hours = Decimal(total_worked_hours.total_seconds()) / Decimal(3600)
            night_hours = Decimal(total_night_hours.total_seconds()) / Decimal(3600)

            # Calcular horas regulares y extra
            biweekly_limit = Decimal(employee.biweekly_hours)
            regular_hours = min(total_hours, biweekly_limit)
            extra_hours = max(Decimal("0"), total_hours - biweekly_limit)
            night_hours = min(night_hours, regular_hours)

            # Estimar salario (sin deducciones)
            regular_pay = regular_hours * employee.salary_hour
            night_premium = (
                night_hours * employee.salary_hour * (employee.night_shift_factor - Decimal("1.0"))
            )
            extra_pay = extra_hours * employee.salary_hour * Decimal("1.5")
            estimated_salary = regular_pay + night_premium + extra_pay

            employees_summary.append(
                {
                    "employee_id": employee.id,
                    "employee_username": employee.username,
                    "employee_full_name": f"{employee.first_name} {employee.last_name}",
                    "total_hours": str(total_hours.quantize(Decimal("0.01"))),
                    "regular_hours": str(regular_hours.quantize(Decimal("0.01"))),
                    "night_hours": str(night_hours.quantize(Decimal("0.01"))),
                    "extra_hours": str(extra_hours.quantize(Decimal("0.01"))),
                    "estimated_salary": str(estimated_salary.quantize(Decimal("0.01"))),
                    "days_worked": len(days_worked),
                    "pending_checkout": pending_checkout,
                }
            )

        return Response(
            {
                "period": {
                    "id": pay_period.id,
                    "description": pay_period.description,
                    "start_date": pay_period.start_date.isoformat(),
                    "end_date": pay_period.end_date.isoformat(),
                    "is_closed": pay_period.is_closed,
                },
                "employees": employees_summary,
                "total_employees": len(employees_summary),
            }
        )
