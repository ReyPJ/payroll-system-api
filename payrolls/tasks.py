from celery import shared_task
from datetime import date, timedelta
from django.utils import timezone
from attendance.models import AttendanceRegister
from timers.models import Timer
from employee.models import Employee
from twilio.rest import Client
from core import settings
import logging
import json


logger = logging.getLogger(__name__)


@shared_task
def remind_pay_period_to_admin():
    today = date.today()
    if today.day == 28 or today.day == 14:
        logger.info(f"Ejecutando remind_pay_period_to_admin. Fecha: {today}")
        employees = Employee.objects.filter(is_admin=True)
        for employee in employees:
            logger.info(
                f"Enviando recordatorio a {employee.username}, al numero {employee.phone}"
            )
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            recipient = f"whatsapp:{employee.phone}"
            variables = {"1": employee.get_full_name()}
            try:
                response = client.messages.create(
                    from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                    to=recipient,
                    content_sid=settings.TWILIO_MESSAGE_TEMPLATE_ID_2,
                    content_variables=json.dumps(variables),
                )
                logger.info(f"Mensaje enviado exitosamente con SID: {response.sid}")
            except Exception as e:
                logger.info(f"Error enviando el mensaje a {recipient}, error: {e}")


@shared_task
def check_attendance():
    now = timezone.localtime()
    today = now.date()
    employees = Employee.objects.filter(phone__isnull=False)

    logger.info(f"Ejecutando check_attendance. Total empleados: {employees.count()}")
    logger.info(f"Hora actual: {now}")

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    for employee in employees:
        logger.info(
            f"--------- Revisando empleado: {employee.username} - {employee.phone} ---------"
        )

        # Verificar si hay asistencia sin cierre (marca de entrada sin salida)
        last_attendance = (
            AttendanceRegister.objects.filter(
                employee=employee, timestamp_out__isnull=True
            )
            .order_by("-timestamp_in")
            .first()
        )

        if last_attendance:
            logger.info(f"Última asistencia (UTC): {last_attendance.timestamp_in}")

            # Extraer la fecha y hora sin zona horaria
            timestamp_values = {
                "year": last_attendance.timestamp_in.year,
                "month": last_attendance.timestamp_in.month,
                "day": last_attendance.timestamp_in.day,
                "hour": last_attendance.timestamp_in.hour,
                "minute": last_attendance.timestamp_in.minute,
                "second": last_attendance.timestamp_in.second,
                "microsecond": last_attendance.timestamp_in.microsecond,
            }

            # Crear un nuevo datetime en zona local con los mismos valores
            naive_dt = timezone.datetime(**timestamp_values)
            timestamp_in_local = timezone.make_aware(
                naive_dt, timezone.get_current_timezone()
            )

            logger.info(f"Última asistencia (ajustada a local): {timestamp_in_local}")

            # Buscar horario del día
            timer = Timer.objects.filter(
                employee=employee,
                day=timestamp_in_local.weekday(),
                is_active=True,
            ).first()

            if timer:
                logger.info(
                    f"Timer encontrado para día {timestamp_in_local.weekday()}: {timer.timeIn} - {timer.timeOut} (is_active={timer.is_active})"
                )

                # Calcular hora de salida programada usando la marca de entrada como base
                scheduled_out_local = timestamp_in_local.replace(
                    hour=timer.timeOut.hour, minute=timer.timeOut.minute, second=0
                )

                # Ajustar si el horario cruza la medianoche
                if timer.timeOut < timer.timeIn:
                    scheduled_out_local += timedelta(days=1)

                logger.info(f"Hora actual (local): {now}")
                logger.info(f"Hora esperada de salida (local): {scheduled_out_local}")
                logger.info(
                    f"Hora esperada de salida + 5min: {scheduled_out_local + timedelta(minutes=5)}"
                )
                logger.info(
                    f"¿La hora actual es mayor? {now > scheduled_out_local + timedelta(minutes=5)}"
                )

                # Solo enviar recordatorio si ya pasó la hora de salida + 5 minutos
                if now > (scheduled_out_local + timedelta(minutes=5)):
                    logger.info(
                        "El empleado no ha marcado salida y ya pasó la hora programada de salida + 5 minutos"
                    )
                    variables = {
                        "1": employee.username,
                        "2": scheduled_out_local.strftime("%H:%M"),
                    }
                    recipient = f"whatsapp:{employee.phone}"
                    try:
                        response = client.messages.create(
                            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                            to=recipient,
                            content_sid=settings.TWILIO_MESSAGE_TEMPLATE_ID,
                            content_variables=json.dumps(variables),
                        )
                        logger.info(
                            f"Mensaje de salida enviado exitosamente con SID: {response.sid}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error enviando mensaje de salida a {recipient}: {e}"
                        )
                else:
                    logger.info(
                        "Aún no es hora de salida o está dentro de la tolerancia de 5 minutos."
                    )
            else:
                logger.info(
                    f"No se encontró horario registrado para este día ({timestamp_in_local.weekday()}) para {employee.username}."
                )
        else:
            logger.info("No se encontró asistencia activa para este empleado.")

            # Verificar si el empleado ya completó un turno hoy (con entrada y salida)
            completed_today = AttendanceRegister.objects.filter(
                employee=employee, timestamp_in__date=today, timestamp_out__isnull=False
            ).exists()

            if completed_today:
                logger.info(
                    f"El empleado {employee.username} ya completó su turno de hoy. No se enviará recordatorio."
                )
                continue

            # Verificar si el empleado debería haber marcado entrada (según horario)
            today_weekday = now.weekday()
            logger.info(
                f"Hoy es día {today_weekday}, buscando timer para {employee.username}"
            )
            timer = Timer.objects.filter(
                employee=employee, day=today_weekday, is_active=True
            ).first()

            if timer:
                logger.info(
                    f"Timer encontrado para {employee.username}: {timer.timeIn} - {timer.timeOut} (is_active={timer.is_active})"
                )

                # Verificar si ya pasó la hora de entrada + 10 minutos de tolerancia
                scheduled_start = now.replace(
                    hour=timer.timeIn.hour, minute=timer.timeIn.minute, second=0
                )

                # Calcular hora de fin del turno
                scheduled_end = now.replace(
                    hour=timer.timeOut.hour, minute=timer.timeOut.minute, second=0
                )
                if timer.timeOut < timer.timeIn:  # Si el turno cruza la medianoche
                    scheduled_end += timedelta(days=1)

                # Comparar horas para ver si estamos en horario de trabajo
                is_after_start_time = now > (scheduled_start + timedelta(minutes=10))
                is_before_end_time = now < scheduled_end

                logger.info(f"Hora actual: {now}")
                logger.info(
                    f"Hora de inicio + 10min: {scheduled_start + timedelta(minutes=10)}"
                )
                logger.info(f"Hora de fin: {scheduled_end}")
                logger.info(f"¿Después de hora inicio+10min? {is_after_start_time}")
                logger.info(f"¿Antes de hora fin? {is_before_end_time}")
                logger.info(
                    f"¿Enviar recordatorio? {is_after_start_time and is_before_end_time}"
                )

                if is_after_start_time and is_before_end_time:
                    logger.info(
                        f"El empleado {employee.username} no ha marcado entrada y debería haberlo hecho"
                    )

                    variables = {
                        "1": employee.username,
                        "2": scheduled_start.strftime("%H:%M"),
                    }
                    recipient = f"whatsapp:{employee.phone}"

                    try:
                        response = client.messages.create(
                            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                            to=recipient,
                            content_sid=settings.TWILIO_MESSAGE_TEMPLATE_ID,
                            content_variables=json.dumps(variables),
                        )
                        logger.info(
                            f"Mensaje recordatorio de entrada enviado exitosamente con SID: {response.sid}"
                        )
                    except Exception as e:
                        logger.error(f"Error enviando mensaje a {recipient}: {e}")
                else:
                    if not is_after_start_time:
                        logger.info(
                            f"Aún está dentro de los 10 minutos de tolerancia para {employee.username}"
                        )
                    elif not is_before_end_time:
                        logger.info(
                            f"Ya pasó la hora de salida del turno para {employee.username} ({scheduled_end}). No se enviará recordatorio de entrada"
                        )
            else:
                logger.info(
                    f"No se encontró timer activo para {employee.username} hoy (día {today_weekday})"
                )
