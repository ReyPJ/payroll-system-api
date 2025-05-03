from rest_framework import generics
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status
from rest_framework.views import APIView
from employee.models import Employee
from payrolls.services.calculate_payroll import calculate_pay_to_go
from payrolls.models import SalaryRecord, PayPeriod
from payrolls.serializers import SalaryRecordSerializer, PayPeriodSerializer
from datetime import date, timedelta
from core.permissions import IsAdmin


class CalculateSalary(generics.RetrieveAPIView):
    serializer_class = SalaryRecordSerializer  # Aquí agregamos el serializador

    def get(self, request, *args, **kwargs):
        try:
            employee = Employee.objects.get(id=kwargs["employee_id"])
        except Employee.DoesNotExist:
            raise NotFound(detail="Empleado no encontrado")

        # Llamamos a la función que calcula el salario
        salary_data = calculate_pay_to_go(employee)

        pay_period = PayPeriod.objects.filter(is_closed=False).first()
        if not pay_period:
            return Response(
                {"error": "No hay período de pago activo"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if SalaryRecord.objects.filter(
            employee=employee, pay_period=pay_period
        ).exists():
            return Response(
                {"error": "Ya se realizó el pago para esta quincena"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Creamos el registro de pago
        salary_record = SalaryRecord.objects.create(
            pay_period=pay_period,  # Referencia al objeto completo
            employee=employee,
            total_hours=salary_data["total_hours"].total_seconds() / 3600,
            extra_hours=salary_data["extra_hours"].total_seconds() / 3600,
            salary_to_pay=salary_data["salary_to_pay"],
        )

        serializer = self.get_serializer(salary_record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ManagePayPeriodView(APIView):
    """
    Vista para manejar los períodos de pago:
    - Cerrar el período actual
    - Crear un nuevo período
    """

    permission_classes = [IsAdmin]

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
