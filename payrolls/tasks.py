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
    employees = Employee.objects.filter(phone__isnull=False)

    logger.info(f"Ejecutando check_attendance. Total empleados: {employees.count()}")

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    for employee in employees:
        logger.info(f"Revisando empleado: {employee.username} - {employee.phone}")

        # Verificar si hay asistencia sin cierre (marca de entrada sin salida)
        last_attendance = (
            AttendanceRegister.objects.filter(
                employee=employee, timestamp_out__isnull=True
            )
            .order_by("-timestamp_in")
            .first()
        )

        if last_attendance:
            logger.info(f"Última asistencia: {last_attendance.timestamp_in}")

            # Buscar horario del día
            timer = Timer.objects.filter(
                employee=employee,
                day=last_attendance.timestamp_in.weekday(),
                is_active=True,
            ).first()

            if timer:
                # Verificar si ha pasado la hora de salida
                scheduled_out = last_attendance.timestamp_in.replace(
                    hour=timer.timeOut.hour, minute=timer.timeOut.minute, second=0
                )

                # Ajustar si el horario cruza la medianoche
                if timer.timeOut < timer.timeIn:
                    scheduled_out += timedelta(days=1)

                logger.info(f"Hora esperada de salida: {scheduled_out}")

                if now > (scheduled_out + timedelta(minutes=10)):
                    logger.info("El empleado está tarde, enviando recordatorio...")

                    variables = {
                        "1": employee.username,
                        "2": scheduled_out.strftime("%H:%M"),
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
                            f"Mensaje enviado exitosamente con SID: {response.sid}"
                        )
                    except Exception as e:
                        logger.error(f"Error enviando mensaje a {recipient}: {e}")
                else:
                    logger.info("No está tarde aún.")
            else:
                logger.info("No se encontró horario registrado para este día.")
        else:
            # Verificar si el empleado debería haber marcado entrada (según horario)
            today_weekday = now.weekday()
            timer = Timer.objects.filter(
                employee=employee, day=today_weekday, is_active=True
            ).first()

            if timer:
                # Verificar si ya pasó la hora de entrada + 10 minutos de tolerancia
                scheduled_start = now.replace(
                    hour=timer.timeIn.hour, minute=timer.timeIn.minute, second=0
                )

                if now > (
                    scheduled_start + timedelta(minutes=10)
                ) and now < scheduled_start.replace(hour=23, minute=59):
                    # Verificar si ya se envió un recordatorio en la última hora
                    # Para evitar spam de mensajes

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

            logger.info("No se encontró asistencia activa para este empleado.")
