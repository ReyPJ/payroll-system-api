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


def calculate_pay_to_go(employee, apply_night_factor=False, period_id=None):
    """
    Calcula el pago para un empleado basado en las marcas registradas en la quincena actual o especificada

    Args:
        employee: Objeto Employee
        apply_night_factor: Booleano que indica si se debe aplicar el factor de pago nocturno
        period_id: ID opcional del período de pago a calcular (si es None, usa el período activo)

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

        # Verificar si el turno es nocturno según Timer
        day_of_week = timestamp_in_local.weekday()
        timer = Timer.objects.filter(
            employee=employee, day=day_of_week, is_active=True
        ).first()

        # Si el timer está configurado como nocturno o si el horario cae en periodo nocturno
        is_night = False
        if timer and timer.is_night_shift:
            is_night = True
        elif is_night_shift(timestamp_in_local, timestamp_out_local):
            is_night = True

        if is_night:
            total_night_hours += worked_hours

        total_worked_hours += worked_hours

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

    # Calcular salario
    regular_pay = regular_hours * employee.salary_hour

    # Calcular pago adicional por nocturnidad (si aplica)
    night_factor = employee.night_shift_factor if apply_night_factor else Decimal("1.0")
    night_premium = night_hours * employee.salary_hour * (night_factor - Decimal("1.0"))

    # Calcular pago por horas extra (siempre 1.5x)
    extra_pay = extra_hours * employee.salary_hour * Decimal("1.5")

    # Total a pagar
    total_pay = regular_pay + night_premium + extra_pay

    # Marcar los registros como pagados
    records.update(paid=True, pay_period=pay_period)

    return {
        "total_hours": total_hours,
        "regular_hours": regular_hours,
        "night_hours": night_hours,
        "extra_hours": extra_hours,
        "night_shift_factor_applied": night_factor,
        "salary_to_pay": total_pay,
    }
