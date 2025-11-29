"""
Management command para resetear el estado 'paid' de asistencias
Útil cuando se calcula salario antes del fin del período y se necesita recalcular
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from attendance.models import AttendanceRegister, AttendanceDetail
from payrolls.models import SalaryRecord, PayPeriod
from employee.models import Employee


class Command(BaseCommand):
    help = """
    Resetea el estado 'paid' de asistencias para poder recalcular salarios correctamente.
    Útil cuando se calcula un salario antes del fin del período.

    Uso:
    1. Para empleados específicos en un período:
       python manage.py reset_attendance_paid_status --period-id=1 --employees 1 2 3

    2. Para todos los empleados en un período:
       python manage.py reset_attendance_paid_status --period-id=1 --all-employees

    3. Con eliminación de registros de salario existentes:
       python manage.py reset_attendance_paid_status --period-id=1 --employees 1 2 3 --delete-salary-records
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--period-id",
            type=int,
            required=True,
            help="ID del período de pago a resetear",
        )
        parser.add_argument(
            "--employees",
            nargs="+",
            type=int,
            help="IDs de empleados a resetear (separados por espacio)",
        )
        parser.add_argument(
            "--all-employees",
            action="store_true",
            help="Resetear para todos los empleados del período",
        )
        parser.add_argument(
            "--delete-salary-records",
            action="store_true",
            help="Eliminar registros de salario existentes para estos empleados",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostrar qué se haría sin hacer cambios reales",
        )

    def handle(self, *args, **options):
        period_id = options["period_id"]
        employee_ids = options.get("employees") or []
        all_employees = options["all_employees"]
        delete_salary = options["delete_salary_records"]
        dry_run = options["dry_run"]

        # Validaciones
        if not employee_ids and not all_employees:
            self.stdout.write(
                self.style.ERROR(
                    "Debes especificar --employees o --all-employees"
                )
            )
            return

        if employee_ids and all_employees:
            self.stdout.write(
                self.style.ERROR(
                    "No puedes usar --employees y --all-employees al mismo tiempo"
                )
            )
            return

        try:
            pay_period = PayPeriod.objects.get(id=period_id)
        except PayPeriod.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Período con ID {period_id} no existe")
            )
            return

        self.stdout.write(
            self.style.WARNING(f"\n{'='*60}")
        )
        self.stdout.write(
            self.style.WARNING(f"RESETEO DE ASISTENCIAS - {'DRY RUN' if dry_run else 'MODO REAL'}")
        )
        self.stdout.write(
            self.style.WARNING(f"{'='*60}\n")
        )
        self.stdout.write(f"Período: {pay_period.description}")
        self.stdout.write(f"Fechas: {pay_period.start_date} - {pay_period.end_date}\n")

        # Obtener empleados a procesar
        if all_employees:
            # Todos los empleados que tienen asistencias en este período
            employee_ids = (
                AttendanceRegister.objects.filter(pay_period=pay_period)
                .values_list("employee_id", flat=True)
                .distinct()
            )
            employees = Employee.objects.filter(id__in=employee_ids)
        else:
            employees = Employee.objects.filter(id__in=employee_ids)

        if not employees.exists():
            self.stdout.write(self.style.ERROR("No se encontraron empleados"))
            return

        self.stdout.write(
            self.style.WARNING(
                f"Empleados a procesar ({employees.count()}):"
            )
        )
        for emp in employees:
            self.stdout.write(f"  - {emp.username} (ID: {emp.id})")

        self.stdout.write("\n")

        # Estadísticas
        total_attendance_reset = 0
        total_details_deleted = 0
        total_salary_deleted = 0

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  MODO DRY RUN - No se harán cambios reales\n"
                )
            )

        # Procesar cada empleado
        for employee in employees:
            self.stdout.write(
                self.style.HTTP_INFO(
                    f"\n--- Procesando: {employee.username} (ID: {employee.id}) ---"
                )
            )

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

            self.stdout.write(f"  Asistencias marcadas como pagadas: {count_paid}")
            self.stdout.write(f"  Detalles de asistencia: {count_details}")
            self.stdout.write(f"  Registros de salario: {count_salary}")

            if count_paid == 0 and count_details == 0 and count_salary == 0:
                self.stdout.write(
                    self.style.WARNING("  ⚠️  No hay nada que resetear para este empleado")
                )
                continue

            # Mostrar información del registro de salario si existe
            if count_salary > 0:
                salary_record = salary_records.first()
                self.stdout.write(
                    f"  Salario actual registrado: ${salary_record.salary_to_pay}"
                )
                self.stdout.write(
                    f"  Horas totales: {salary_record.total_hours}"
                )
                self.stdout.write(
                    f"  Fecha de cálculo: {salary_record.paid_at}"
                )

            if not dry_run:
                with transaction.atomic():
                    # Resetear asistencias
                    if count_paid > 0:
                        updated = paid_attendance.update(paid=False)
                        total_attendance_reset += updated
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ {updated} asistencias reseteadas a paid=False"
                            )
                        )

                    # Eliminar detalles de asistencia
                    if count_details > 0:
                        deleted_count = attendance_details.delete()[0]
                        total_details_deleted += deleted_count
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ {deleted_count} detalles de asistencia eliminados"
                            )
                        )

                    # Eliminar registros de salario si se solicita
                    if delete_salary and count_salary > 0:
                        deleted_count = salary_records.delete()[0]
                        total_salary_deleted += deleted_count
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ {deleted_count} registros de salario eliminados"
                            )
                        )
                    elif count_salary > 0:
                        self.stdout.write(
                            self.style.WARNING(
                                "  ⚠️  Registro de salario NO eliminado (usa --delete-salary-records para eliminarlo)"
                            )
                        )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [DRY RUN] Se resetearían {count_paid} asistencias"
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"  [DRY RUN] Se eliminarían {count_details} detalles de asistencia"
                    )
                )
                if delete_salary and count_salary > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [DRY RUN] Se eliminarían {count_salary} registros de salario"
                        )
                    )

        # Resumen final
        self.stdout.write(
            self.style.WARNING(f"\n{'='*60}")
        )
        self.stdout.write(
            self.style.WARNING("RESUMEN")
        )
        self.stdout.write(
            self.style.WARNING(f"{'='*60}")
        )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Asistencias reseteadas: {total_attendance_reset}"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Detalles eliminados: {total_details_deleted}"
                )
            )
            if delete_salary:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Registros de salario eliminados: {total_salary_deleted}"
                    )
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ COMPLETADO - Los empleados están listos para recalcular"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  DRY RUN completado - No se hicieron cambios reales"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Ejecuta sin --dry-run para aplicar los cambios"
                )
            )

        self.stdout.write("")
