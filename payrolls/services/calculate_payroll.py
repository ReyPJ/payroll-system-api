from django.utils import timezone
from django.utils.timezone import localtime
from datetime import timedelta, time
from attendance.models import AttendanceRegister
from timers.models import Timer
from decimal import Decimal
from payrolls.models import PayPeriod


def is_night_shift(start_time, end_time):
    """
    Determina si un turno es nocturno
    Se considera nocturno si:
    - Inicia después de las 7pm o antes de las 6am
    - O termina después de las 7pm o antes de las 6am
    """
    night_start = time(19, 0)  # 7:00 PM
    night_end = time(6, 0)  # 6:00 AM

    # Convertir a objetos time si son datetime
    if hasattr(start_time, "time"):
        start_time = start_time.time()
    if hasattr(end_time, "time"):
        end_time = end_time.time()

    # Si el turno cruza la medianoche
    if end_time < start_time:
        return True

    # Si inicia en horario nocturno
    if start_time >= night_start or start_time < night_end:
        return True

    # Si termina en horario nocturno
    if end_time > night_start or end_time <= night_end:
        return True

    return False


def calculate_pay_to_go(
    employee,
    apply_night_factor=False,
    period_id=None,
    lunch_deduction_hours=0,
    other_deductions=0,
    other_deductions_description="",
):
    """
    Calcula el pago para un empleado basado en las marcas registradas en la quincena actual o especificada

    Args:
        employee: Objeto Employee
        apply_night_factor: Booleano que indica si se debe aplicar el factor de pago nocturno
        period_id: ID opcional del período de pago a calcular (si es None, usa el período activo)
        lunch_deduction_hours: Horas a deducir por almuerzo
        other_deductions: Otras deducciones monetarias
        other_deductions_description: Descripción de las otras deducciones

    Returns:
        Diccionario con las horas calculadas y salario a pagar
    """
    if period_id:
        try:
            pay_period = PayPeriod.objects.get(id=period_id)
        except PayPeriod.DoesNotExist:
            return {"error": f"No existe un período de pago con ID {period_id}"}
    else:
        # Usar el período activo (no cerrado)
        today = timezone.now().date()
        pay_period = PayPeriod.objects.filter(
            start_date__lte=today, end_date__gte=today, is_closed=False
        ).first()

        if not pay_period:
            return {"error": "No hay quincena activa"}

    records = AttendanceRegister.objects.filter(
        employee=employee,
        timestamp_in__date__gte=pay_period.start_date,
        timestamp_in__date__lte=pay_period.end_date,
        paid=False,
    ).order_by("timestamp_in")

    if not records.exists():
        return {
            "error": f"No hay registros sin pagar para el empleado en el período {pay_period.description}"
        }

    total_worked_hours = timedelta()
    total_night_hours = timedelta()

    # Diccionario para almacenar detalles diarios de asistencia
    attendance_details = {}

    # Procesar cada registro de asistencia
    for record in records:
        # Omitir registros sin marca de salida
        if not record.timestamp_out:
            continue

        timestamp_in_local = localtime(record.timestamp_in)
        timestamp_out_local = localtime(record.timestamp_out)

        # Validar orden correcto de tiempos
        if timestamp_out_local <= timestamp_in_local:
            continue

        worked_hours = timestamp_out_local - timestamp_in_local
        work_date = timestamp_in_local.date()

        # Verificar si el turno es nocturno según Timer
        day_of_week = timestamp_in_local.weekday()
        timer = Timer.objects.filter(
            employee=employee, day=day_of_week, is_active=True
        ).first()

        # Si el timer está configurado como nocturno o si el horario cae en periodo nocturno
        is_night = False
        if timer and timer.is_night_shift:
            is_night = True
        elif is_night_shift(timestamp_in_local.time(), timestamp_out_local.time()):
            is_night = True

        if is_night:
            total_night_hours += worked_hours
            night_hours_for_day = worked_hours
            regular_hours_for_day = timedelta(0)
        else:
            night_hours_for_day = timedelta(0)
            regular_hours_for_day = worked_hours

        total_worked_hours += worked_hours

        # Guardar detalles de este día
        if work_date not in attendance_details:
            attendance_details[work_date] = {
                "time_in": timestamp_in_local.time(),
                "time_out": timestamp_out_local.time(),
                "regular_hours": regular_hours_for_day,
                "night_hours": night_hours_for_day,
                "extra_hours": timedelta(0),  # Se calculará después
                "lunch_deduction": timedelta(0),  # Se aplicará proporcionalmente
            }
        else:
            # Si ya hay un registro para este día, actualizar las horas
            attendance_details[work_date]["regular_hours"] += regular_hours_for_day
            attendance_details[work_date]["night_hours"] += night_hours_for_day

            # Actualizar hora de entrada/salida si es necesario
            if timestamp_in_local.time() < attendance_details[work_date]["time_in"]:
                attendance_details[work_date]["time_in"] = timestamp_in_local.time()
            if timestamp_out_local.time() > attendance_details[work_date]["time_out"]:
                attendance_details[work_date]["time_out"] = timestamp_out_local.time()

    # Convertir a decimal para cálculos precisos
    total_seconds = Decimal(total_worked_hours.total_seconds())
    night_seconds = Decimal(total_night_hours.total_seconds())

    # Convertir a horas
    total_hours = total_seconds / Decimal(3600)
    night_hours = night_seconds / Decimal(3600)

    # Calcular horas regulares (limitadas al máximo biweekly) y extra
    biweekly_limit = Decimal(employee.biweekly_hours)
    regular_hours = min(total_hours, biweekly_limit)
    extra_hours = max(Decimal("0"), total_hours - biweekly_limit)

    # Limitar horas nocturnas al máximo de horas regulares
    night_hours = min(night_hours, regular_hours)

    # Aplicar deducción de almuerzo
    lunch_deduction_hours = Decimal(lunch_deduction_hours)

    # Distribuir las horas extra a los detalles diarios si hay horas extra
    if extra_hours > 0:
        # Convertir horas extra a segundos
        extra_seconds = extra_hours * 3600

        # Calcular el total de segundos trabajados en cada día
        daily_totals = {
            date: (details["regular_hours"] + details["night_hours"]).total_seconds()
            for date, details in attendance_details.items()
        }

        # Calcular el total de todos los días
        all_days_total = sum(daily_totals.values())

        # Distribuir las horas extra proporcionalmente
        for date, total_seconds in daily_totals.items():
            # Calcular la proporción de este día en relación al total
            proportion = Decimal(total_seconds) / Decimal(all_days_total)
            # Asignar horas extra proporcionalmente
            extra_seconds_for_day = proportion * extra_seconds
            attendance_details[date]["extra_hours"] = timedelta(
                seconds=int(extra_seconds_for_day)
            )

    # Distribuir la deducción de almuerzo proporcionalmente a los días trabajados si hay deducción
    if lunch_deduction_hours > 0:
        lunch_seconds = lunch_deduction_hours * 3600
        days_count = len(attendance_details)

        if days_count > 0:
            lunch_seconds_per_day = lunch_seconds / days_count
            for date in attendance_details:
                attendance_details[date]["lunch_deduction"] = timedelta(
                    seconds=int(lunch_seconds_per_day)
                )

    # Calcular salario
    regular_pay = regular_hours * employee.salary_hour

    # Calcular pago adicional por nocturnidad (si aplica)
    night_factor = employee.night_shift_factor if apply_night_factor else Decimal("1.0")
    night_premium = night_hours * employee.salary_hour * (night_factor - Decimal("1.0"))

    # Calcular pago por horas extra (siempre 1.5x)
    extra_pay = extra_hours * employee.salary_hour * Decimal("1.5")

    # Calcular deducciones
    lunch_deduction = lunch_deduction_hours * employee.salary_hour
    other_deductions = Decimal(other_deductions)

    # Salario bruto antes de deducciones
    gross_salary = regular_pay + night_premium + extra_pay

    # Total a pagar después de deducciones
    total_pay = gross_salary - lunch_deduction - other_deductions

    # Marcar los registros como pagados
    records.update(paid=True, pay_period=pay_period)

    # Guardar los detalles de asistencia
    from attendance.models import AttendanceDetail

    for work_date, details in attendance_details.items():
        # Convertir timedeltas a decimal para guardar en el modelo
        regular_hours_decimal = Decimal(
            details["regular_hours"].total_seconds()
        ) / Decimal(3600)
        night_hours_decimal = Decimal(details["night_hours"].total_seconds()) / Decimal(
            3600
        )
        extra_hours_decimal = Decimal(details["extra_hours"].total_seconds()) / Decimal(
            3600
        )
        lunch_deduction_decimal = Decimal(
            details["lunch_deduction"].total_seconds()
        ) / Decimal(3600)

        # Crear o actualizar el detalle de asistencia
        AttendanceDetail.objects.update_or_create(
            employee=employee,
            pay_period=pay_period,
            work_date=work_date,
            defaults={
                "time_in": details["time_in"],
                "time_out": details["time_out"],
                "regular_hours": regular_hours_decimal,
                "night_hours": night_hours_decimal,
                "extra_hours": extra_hours_decimal,
                "lunch_deduction": lunch_deduction_decimal,
            },
        )

    return {
        "total_hours": total_hours,
        "regular_hours": regular_hours,
        "night_hours": night_hours,
        "extra_hours": extra_hours,
        "night_shift_factor_applied": night_factor,
        "gross_salary": gross_salary,
        "lunch_deduction_hours": lunch_deduction_hours,
        "other_deductions": other_deductions,
        "other_deductions_description": other_deductions_description,
        "salary_to_pay": total_pay,
    }
