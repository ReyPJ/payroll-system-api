from datetime import datetime, time, timedelta
from decimal import ROUND_DOWN, Decimal

from django.utils import timezone
from django.utils.timezone import localtime

from attendance.models import AttendanceRegister
from payrolls.models import PayPeriod
from timers.models import Timer


def truncate_seconds(dt):
    """
    Trunca los segundos y microsegundos de un datetime.
    Solo mantiene horas y minutos para cálculos de nómina.

    Args:
        dt: datetime object

    Returns:
        datetime con segundos y microsegundos en 0
    """
    return dt.replace(second=0, microsecond=0)


def truncate_timedelta_to_minutes(td):
    """
    Trunca un timedelta para que solo contenga horas y minutos completos.
    Elimina segundos y microsegundos del cálculo.

    Args:
        td: timedelta object

    Returns:
        timedelta con solo horas y minutos (sin segundos)
    """
    total_minutes = int(td.total_seconds() // 60)
    return timedelta(minutes=total_minutes)


def round_early_entry(timestamp_in):
    """
    Redondea entradas tempranas (entre 7:00 AM y 7:59 AM) a las 8:00 AM.
    Esto evita que empleados que marcan antes de su hora de entrada
    acumulen tiempo extra no autorizado.

    Args:
        timestamp_in: datetime de la marca de entrada

    Returns:
        datetime ajustado (8:00 AM si entró entre 7:00-7:59 AM)
    """
    hour = timestamp_in.hour

    # Si marcó entre 7:00 AM y 7:59 AM, redondear a 8:00 AM
    if hour == 7:
        return timestamp_in.replace(hour=8, minute=0, second=0, microsecond=0)

    return timestamp_in


def calculate_night_hours(timestamp_in, timestamp_out):
    """
    Calcula las horas nocturnas reales trabajadas en un turno.
    Horario nocturno: 7:00 PM (19:00) a 6:00 AM (06:00)

    Returns:
        timedelta: Horas trabajadas en horario nocturno
    """
    night_start = time(19, 0)  # 7:00 PM
    night_end = time(6, 0)  # 6:00 AM

    total_night = timedelta()
    current = timestamp_in

    while current < timestamp_out:
        current_time = current.time()

        # Calcular hasta dónde avanzar (máximo 1 hora o hasta timestamp_out)
        next_hour = current + timedelta(hours=1)
        if next_hour > timestamp_out:
            next_hour = timestamp_out

        # Verificar si esta hora está en período nocturno
        # Nocturno es: >= 19:00 O < 06:00
        is_night_hour = current_time >= night_start or current_time < night_end

        if is_night_hour:
            total_night += next_hour - current

        current = next_hour

    return total_night


def is_night_shift(start_time, end_time):
    """
    DEPRECATED: Usa calculate_night_hours() en su lugar.
    Esta función solo determina SI hay horas nocturnas, no CUÁNTAS.

    Determina si un turno tiene alguna hora nocturna.
    Se considera que tiene horas nocturnas si:
    - Alguna parte del turno cae entre 7pm y 6am
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
    other_deductions=0,
    other_deductions_description="",
):
    """
    Calcula el pago para un empleado basado en las marcas registradas en la quincena actual o especificada

    Args:
        employee: Objeto Employee
        apply_night_factor: Booleano que indica si se debe aplicar el factor de pago nocturno
        period_id: ID opcional del período de pago a calcular (si es None, usa el período activo)
        other_deductions: Otras deducciones monetarias
        other_deductions_description: Descripción de las otras deducciones

    Returns:
        Diccionario con las horas calculadas y salario a pagar

    Note:
        Las horas de almuerzo se calculan automáticamente como 1 hora por cada día trabajado
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

        # CAMBIO 1: Truncar segundos y microsegundos (solo contar horas y minutos)
        timestamp_in_local = truncate_seconds(timestamp_in_local)
        timestamp_out_local = truncate_seconds(timestamp_out_local)

        # CAMBIO 2: Redondear entradas tempranas (7:XX AM -> 8:00 AM)
        timestamp_in_local = round_early_entry(timestamp_in_local)

        # Validar orden correcto de tiempos
        if timestamp_out_local <= timestamp_in_local:
            continue

        worked_hours = timestamp_out_local - timestamp_in_local
        # Truncar el timedelta resultante también (por seguridad)
        worked_hours = truncate_timedelta_to_minutes(worked_hours)
        work_date = timestamp_in_local.date()

        # Verificar si el turno es nocturno según Timer
        day_of_week = timestamp_in_local.weekday()
        timer = Timer.objects.filter(
            employee=employee, day=day_of_week, is_active=True
        ).first()

        # Calcular horas nocturnas REALES (no binario)
        # Si el timer está marcado como nocturno, todas las horas cuentan como nocturnas
        if timer and timer.is_night_shift:
            night_hours_for_day = worked_hours
            regular_hours_for_day = timedelta(0)
        else:
            # Calcular solo las horas que realmente cayeron en horario nocturno
            night_hours_for_day = calculate_night_hours(
                timestamp_in_local, timestamp_out_local
            )
            regular_hours_for_day = worked_hours - night_hours_for_day

        total_night_hours += night_hours_for_day
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

    # CAMBIO 3: Calcular deducción de almuerzo automáticamente:
    # Solo 1 hora por cada día donde se trabajó >= 7 horas
    # Si el turno es menor a 7 horas, NO se rebaja almuerzo ese día
    MINIMUM_HOURS_FOR_LUNCH_DEDUCTION = 7
    days_with_lunch_deduction = 0

    for work_date, details in attendance_details.items():
        # Calcular horas totales trabajadas ese día
        daily_worked_hours = (
            details["regular_hours"] + details["night_hours"]
        ).total_seconds() / 3600

        if daily_worked_hours >= MINIMUM_HOURS_FOR_LUNCH_DEDUCTION:
            days_with_lunch_deduction += 1
            # Marcar que este día tiene deducción de almuerzo
            details["applies_lunch_deduction"] = True
        else:
            details["applies_lunch_deduction"] = False

    lunch_deduction_hours = Decimal(days_with_lunch_deduction)

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

    # Aplicar deducción de almuerzo solo a los días que califican (>= 7 horas trabajadas)
    if lunch_deduction_hours > 0:
        # 1 hora de deducción por día que califica
        for date, details in attendance_details.items():
            if details.get("applies_lunch_deduction", False):
                attendance_details[date]["lunch_deduction"] = timedelta(hours=1)
            else:
                attendance_details[date]["lunch_deduction"] = timedelta(0)

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
