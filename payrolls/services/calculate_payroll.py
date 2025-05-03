from django.utils.timezone import localtime
from datetime import timedelta, timezone
from attendance.models import AttendanceRegister
from timers.models import Timer
from decimal import Decimal
from payrolls.models import PayPeriod


def calculate_pay_to_go(employee, test_timestamp_in=None, test_timestamp_out=None):

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
    )
    if not records.exists():
        return {"error": "No hay registros para esta quincena"}
    total_hours = timedelta()
    extra_hours = timedelta()

    timers = {
        timer.day: timer
        for timer in Timer.objects.filter(employee=employee, is_active=True)
    }

    for record in records:
        timestamp_in = test_timestamp_in or record.timestamp_in
        timestamp_out = test_timestamp_out or record.timestamp_out

        if timestamp_in and timestamp_out:
            timestamp_in_local = localtime(timestamp_in)
            timestamp_out_local = localtime(timestamp_out)

            # Validar orden correcto de tiempos
            if timestamp_out_local <= timestamp_in_local:
                continue

            worked_hours = timestamp_out_local - timestamp_in_local
            day_of_week = timestamp_in_local.weekday()
            timer = timers.get(day_of_week)

            if timer:
                # Calcular horas según el timer y las horas esperadas

                # Crear datetime completo para el timer de entrada
                timer_start = timestamp_in_local.replace(
                    hour=timer.timeIn.hour,
                    minute=timer.timeIn.minute,
                    second=0,
                    microsecond=0,
                )

                # Calcular la hora de salida esperada basada en horas_esperadas
                expected_duration = timedelta(hours=float(timer.expected_hours))
                timer_end = timer_start + expected_duration

                # Calcular horas extras antes del horario normal
                if timestamp_in_local < timer_start:
                    extra_start = timestamp_in_local
                    extra_end = min(timer_start, timestamp_out_local)
                    extra_hours += extra_end - extra_start

                # Calcular horas extras después del horario normal
                if timestamp_out_local > timer_end:
                    extra_start = max(timer_end, timestamp_in_local)
                    extra_end = timestamp_out_local
                    extra_hours += extra_end - extra_start

                # Calcular horas normales (solapamiento)
                overlap_start = max(timestamp_in_local, timer_start)
                overlap_end = min(timestamp_out_local, timer_end)
                if overlap_start < overlap_end:
                    total_hours += overlap_end - overlap_start

            else:
                # Si no hay timer, todo es extra
                extra_hours += worked_hours

    # Cálculo de salarios
    normal_seconds = Decimal(total_hours.total_seconds())
    extra_seconds = Decimal(extra_hours.total_seconds())
    normal_salary = (normal_seconds / Decimal(3600)) * employee.salary_hour
    extra_salary = (extra_seconds / Decimal(3600)) * (
        employee.salary_hour * Decimal("1.5")
    )

    records.update(
        paid=True, pay_period=pay_period  # Actualizado para usar la relación
    )

    return {
        "total_hours": total_hours,
        "extra_hours": extra_hours,
        "salary_to_pay": normal_salary + extra_salary,
    }
