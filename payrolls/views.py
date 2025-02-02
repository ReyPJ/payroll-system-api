from rest_framework import generics
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status
from employee.models import Employee
from payrolls.services.calculate_payroll import calculate_pay_to_go
from payrolls.models import SalaryRecord, PayPeriod
from payrolls.serializers import SalaryRecordSerializer


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
            employee=employee, pay_period=pay_period.start_date
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
