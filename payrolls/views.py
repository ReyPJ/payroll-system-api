from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status
from rest_framework.views import APIView
from employee.models import Employee
from payrolls.services.calculate_payroll import calculate_pay_to_go
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee_id = serializer.validated_data["employee_id"]
        apply_night_factor = serializer.validated_data.get("apply_night_factor", False)
        period_id = serializer.validated_data.get("period_id", None)
        lunch_deduction_hours = serializer.validated_data.get(
            "lunch_deduction_hours", 0
        )
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

        # Verificar si ya existe un SalaryRecord para este empleado y período
        salary_record = SalaryRecord.objects.filter(
            employee=employee, pay_period=pay_period
        ).first()

        # Llamamos a la función que calcula el salario con el period_id si se proporcionó
        salary_data = calculate_pay_to_go(
            employee,
            apply_night_factor,
            period_id,
            lunch_deduction_hours,
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
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ManagePayPeriodView(APIView):
    """
    Vista para manejar los períodos de pago:
    - Obtener períodos de pago (activos/cerrados)
    - Cerrar el período actual
    - Crear un nuevo período
    """

    permission_classes = [permissions.AllowAny]
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
        if action not in ["close_current", "create_new"]:
            return Response(
                {"error": "Acción no válida. Use 'close_current' o 'create_new'"},
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
            if "end_date" in request.data:
                end_date = request.data.get("end_date")

            new_period = PayPeriod.objects.create(
                start_date=start_date, end_date=end_date, is_closed=False
            )

            serializer = PayPeriodSerializer(new_period)
            return Response(
                {"message": "Nuevo período creado", "period": serializer.data},
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

                # Verificar si el turno es nocturno
                day_of_week = timestamp_in_local.weekday()
                timer = Timer.objects.filter(
                    employee=employee, day=day_of_week, is_active=True
                ).first()

                is_night = False
                if timer and timer.is_night_shift:
                    is_night = True
                elif calculate_pay_to_go.is_night_shift(
                    timestamp_in_local, timestamp_out_local
                ):
                    is_night = True

                if is_night:
                    has_night_hours = True
                    total_night_hours += timestamp_out_local - timestamp_in_local

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
        lunch_deduction_hours = serializer.validated_data.get(
            "lunch_deduction_hours", 0
        )
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
                lunch_deduction_hours=lunch_deduction_hours,
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

        return Response(
            {
                "message": "Cálculo de planilla completado",
                "records": serializer.data,
                "total_planilla": total_planilla,
                "empleados_procesados": len(salary_records),
            }
        )


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
