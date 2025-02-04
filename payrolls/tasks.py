from celery import shared_task
from datetime import date, timedelta
from django.utils import timezone
from payrolls.models import PayPeriod
from attendance.models import AttendanceRegister
from timers.models import Timer
from employee.models import Employee
from twilio.rest import Client
from core import settings
import logging
import json


logger = logging.getLogger(__name__)


@shared_task
def create_pay_periods():
    today = date.today()

    if today.day <= 15:
        start = today.replace(day=1)
        end = today.replace(day=15)
    else:
        start = today.replace(day=16)
        end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(
            days=1
        )

    PayPeriod.objects.get_or_create(
        start_date=start, end_date=end, defaults={"is_closed": False}
    )


@shared_task
def check_attendance():
    now = timezone.localtime()
    employees = Employee.objects.filter(phone__isnull=False)

    logger.info(f"Ejecutando check_attendance. Total empleados: {employees.count()}")

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    for employee in employees:
        logger.info(f"Revisando empleado: {employee.username} - {employee.phone}")

        last_attendance = (
            AttendanceRegister.objects.filter(
                employee=employee, timestamp_out__isnull=True
            )
            .order_by("-timestamp_in")
            .first()
        )

        if last_attendance:
            logger.info(f"Última asistencia: {last_attendance.timestamp_in}")

            timer = Timer.objects.filter(
                employee=employee, day=last_attendance.timestamp_in.weekday()
            ).first()

            if timer:
                scheduled_end = last_attendance.timestamp_in.replace(
                    hour=timer.timeOut.hour, minute=timer.timeOut.minute, second=0
                )

                logger.info(f"Hora programada de salida: {scheduled_end}")

                if now > (scheduled_end + timedelta(minutes=15)):
                    logger.info("El empleado está tarde, enviando recordatorio...")

                    variables = {
                        "1": employee.username,
                        "2": scheduled_end.strftime("%H:%M"),
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
            logger.info("No se encontró asistencia activa para este empleado.")
