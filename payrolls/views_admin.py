"""
Vistas administrativas temporales para operaciones de mantenimiento
IMPORTANTE: Estas vistas deben ser usadas con cuidado y solo por administradores
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db import transaction
from attendance.models import AttendanceRegister, AttendanceDetail
from payrolls.models import SalaryRecord, PayPeriod
from employee.models import Employee


class ResetAttendancePaidStatusView(APIView):
    """
    Endpoint temporal para resetear el estado 'paid' de asistencias.
    Útil cuando se calcula un salario antes del fin del período.

    ⚠️ SOLO PARA ADMINISTRADORES - Requiere autenticación

    POST /payrolls/admin/reset-attendance/
    Body:
    {
        "period_id": 5,
        "employee_ids": [10, 15, 20],  // o "all" para todos
        "delete_salary_records": true,  // opcional, default: false
        "dry_run": false  // opcional, default: false
    }

    Respuesta exitosa:
    {
        "message": "Operación completada",
        "dry_run": false,
        "summary": {
            "employees_processed": 3,
            "attendance_reset": 42,
            "details_deleted": 42,
            "salary_records_deleted": 3
        },
        "employees": [...]
    }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Validar que el usuario sea staff o superuser
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "No tienes permisos para realizar esta operación"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Obtener parámetros
        period_id = request.data.get("period_id")
        employee_ids = request.data.get("employee_ids")
        delete_salary = request.data.get("delete_salary_records", False)
        dry_run = request.data.get("dry_run", False)

        # Validaciones
        if not period_id:
            return Response(
                {"error": "El campo 'period_id' es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not employee_ids:
            return Response(
                {"error": "El campo 'employee_ids' es requerido. Usa 'all' para todos los empleados o una lista de IDs [1, 2, 3]"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pay_period = PayPeriod.objects.get(id=period_id)
        except PayPeriod.DoesNotExist:
            return Response(
                {"error": f"No existe un período de pago con ID {period_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Obtener empleados a procesar
        if employee_ids == "all":
            # Todos los empleados que tienen asistencias en este período
            employee_ids_list = (
                AttendanceRegister.objects.filter(pay_period=pay_period)
                .values_list("employee_id", flat=True)
                .distinct()
            )
            employees = Employee.objects.filter(id__in=employee_ids_list)
        else:
            if not isinstance(employee_ids, list):
                return Response(
                    {"error": "employee_ids debe ser una lista de IDs o 'all'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            employees = Employee.objects.filter(id__in=employee_ids)

        if not employees.exists():
            return Response(
                {"error": "No se encontraron empleados con los IDs especificados"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Estadísticas
        total_attendance_reset = 0
        total_details_deleted = 0
        total_salary_deleted = 0
        employees_data = []

        # Procesar cada empleado
        for employee in employees:
            # Contar asistencias marcadas como pagadas
            paid_attendance = AttendanceRegister.objects.filter(
                employee=employee,
                pay_period=pay_period,
                paid=True,
            )
            count_paid = paid_attendance.count()

            # Contar detalles de asistencia
            attendance_details = AttendanceDetail.objects.filter(
                employee=employee,
                pay_period=pay_period,
            )
            count_details = attendance_details.count()

            # Contar registros de salario
            salary_records = SalaryRecord.objects.filter(
                employee=employee,
                pay_period=pay_period,
            )
            count_salary = salary_records.count()

            employee_info = {
                "employee_id": employee.id,
                "employee_username": employee.username,
                "attendance_to_reset": count_paid,
                "details_to_delete": count_details,
                "salary_records_to_delete": count_salary if delete_salary else 0,
            }

            # Información del registro de salario si existe
            if count_salary > 0:
                salary_record = salary_records.first()
                employee_info["current_salary_info"] = {
                    "salary_to_pay": str(salary_record.salary_to_pay),
                    "total_hours": str(salary_record.total_hours),
                    "calculated_at": salary_record.paid_at.isoformat(),
                }

            if not dry_run:
                with transaction.atomic():
                    # Resetear asistencias
                    if count_paid > 0:
                        updated = paid_attendance.update(paid=False)
                        total_attendance_reset += updated
                        employee_info["attendance_reset"] = updated

                    # Eliminar detalles de asistencia
                    if count_details > 0:
                        deleted_count = attendance_details.delete()[0]
                        total_details_deleted += deleted_count
                        employee_info["details_deleted"] = deleted_count

                    # Eliminar registros de salario si se solicita
                    if delete_salary and count_salary > 0:
                        deleted_count = salary_records.delete()[0]
                        total_salary_deleted += deleted_count
                        employee_info["salary_records_deleted"] = deleted_count

            employees_data.append(employee_info)

        # Construir respuesta
        response_data = {
            "message": "Dry run completado - No se hicieron cambios" if dry_run else "Operación completada exitosamente",
            "dry_run": dry_run,
            "period": {
                "id": pay_period.id,
                "description": pay_period.description,
                "start_date": pay_period.start_date.isoformat(),
                "end_date": pay_period.end_date.isoformat(),
            },
            "summary": {
                "employees_processed": employees.count(),
                "attendance_reset": total_attendance_reset,
                "details_deleted": total_details_deleted,
                "salary_records_deleted": total_salary_deleted,
            },
            "employees": employees_data,
        }

        if dry_run:
            response_data["next_steps"] = [
                "Revisa los datos arriba",
                "Si todo se ve correcto, ejecuta nuevamente con dry_run=false",
                "Después podrás recalcular los salarios normalmente",
            ]
        else:
            response_data["next_steps"] = [
                "Los empleados están listos para recalcular",
                f"Usa POST /payrolls/calculate/ para recalcular individualmente",
                f"O usa GET /payrolls/calculate-all/?period_id={period_id} para todos",
            ]

        return Response(response_data, status=status.HTTP_200_OK)
