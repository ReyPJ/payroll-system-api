import os
import django
import random
from datetime import datetime, timedelta, date, time
from decimal import Decimal

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# Importar modelos después de configurar Django
from employee.models import Employee  # noqa: E402
from payrolls.models import PayPeriod  # noqa: E402
from attendance.models import AttendanceRegister  # noqa: E402
from timers.models import Timer  # noqa: E402
from django.utils import timezone  # noqa: E402

print("Creando datos de prueba para el sistema de nómina...")

# Limpiar datos existentes
print("Limpiando datos existentes...")
Timer.objects.all().delete()
AttendanceRegister.objects.all().delete()
PayPeriod.objects.filter(is_closed=False).delete()  # Solo eliminar período activo

# Crear o actualizar 4 empleados
print("Creando empleados...")
employees = []

# Empleados regulares
employee_data = [
    {
        "username": "maria",
        "first_name": "María",
        "last_name": "González",
        "email": "maria@example.com",
        "salary_hour": Decimal("30.00"),
        "biweekly_hours": Decimal("96.0"),
        "use_finger_print": True,
        "fingerprint_hash": "maria_hash_test",
        "night_shift_factor": Decimal("1.25"),
    },
    {
        "username": "juan",
        "first_name": "Juan",
        "last_name": "Perez",
        "email": "juan@example.com",
        "salary_hour": Decimal("25.00"),
        "biweekly_hours": Decimal("80.0"),
        "use_finger_print": False,
        "face_tamplate": "juan_face_template",
        "night_shift_factor": Decimal("1.20"),
    },
    {
        "username": "carlos",
        "first_name": "Carlos",
        "last_name": "Rodriguez",
        "email": "carlos@example.com",
        "salary_hour": Decimal("28.00"),
        "biweekly_hours": Decimal("96.0"),
        "unique_pin": "123456",
    },
]

# Agregar usuarios vacilones solo con PIN
pin_users = [
    {
        "username": "tralalero",
        "first_name": "Tralalero",
        "last_name": "El Vacilón",
        "email": "tralalero@ejemplo.com",
        "salary_hour": Decimal("20.00"),
        "biweekly_hours": Decimal("96.0"),
        "night_shift_factor": Decimal("1.00"),
        "unique_pin": "55555",
    },
    {
        "username": "tralala",
        "first_name": "Tralala",
        "last_name": "La Vacilona",
        "email": "tralala@ejemplo.com",
        "salary_hour": Decimal("20.00"),
        "biweekly_hours": Decimal("96.0"),
        "night_shift_factor": Decimal("1.00"),
        "unique_pin": "33333",
    },
]

employee_data.extend(pin_users)

for data in employee_data:
    username = data.pop("username")
    emp, created = Employee.objects.get_or_create(username=username, defaults=data)
    if created:
        emp.set_password("password123")
        emp.save()
        print(f"Creado empleado: {emp.username}")
    else:
        print(f"Empleado ya existe: {emp.username}")

    employees.append(emp)

# Crear un período de pago activo
print("Creando período de pago activo...")
start_date = date.today() - timedelta(days=10)
end_date = start_date + timedelta(days=15)
pay_period, created = PayPeriod.objects.get_or_create(
    start_date=start_date,
    end_date=end_date,
    is_closed=False,
    defaults={"description": f"Quincena {start_date} - {end_date}"},
)
if created:
    print(f"Creado período de pago: {pay_period.description}")
else:
    print(f"Ya existe un período activo: {pay_period.description}")

# Crear horarios (timers) para cada empleado
print("Creando horarios para los empleados...")
for emp in employees:
    # Verificar si ya tienen horarios
    if Timer.objects.filter(employee=emp).exists():
        print(f"El empleado {emp.username} ya tiene horarios configurados")
        continue

    # Para María: turno diurno de lunes a viernes (8am-5pm)
    if emp.username == "maria":
        for day in range(5):  # Lunes a viernes
            Timer.objects.create(
                employee=emp,
                day=day,
                timeIn=time(8, 0),
                timeOut=time(17, 0),
                is_active=True,
                is_night_shift=False,
            )
    # Para Juan: turno nocturno lunes, miércoles y viernes (10pm-6am)
    elif emp.username == "juan":
        for day in [0, 2, 4]:  # Lunes, Miércoles, Viernes
            Timer.objects.create(
                employee=emp,
                day=day,
                timeIn=time(22, 0),
                timeOut=time(6, 0),
                is_active=True,
                is_night_shift=True,
            )
    # Para Carlos: horario mixto
    elif emp.username == "carlos":
        # Día (martes y jueves)
        for day in [1, 3]:
            Timer.objects.create(
                employee=emp,
                day=day,
                timeIn=time(9, 0),
                timeOut=time(18, 0),
                is_active=True,
                is_night_shift=False,
            )
        # Noche (sábado)
        Timer.objects.create(
            employee=emp,
            day=5,  # sábado
            timeIn=time(22, 0),
            timeOut=time(7, 0),
            is_active=True,
            is_night_shift=True,
        )
    # Para los vacilones: horario 24/7
    elif emp.username in ["tralalero", "tralala"]:
        for day in range(7):  # Todos los días
            Timer.objects.create(
                employee=emp,
                day=day,
                timeIn=time(0, 0),
                timeOut=time(23, 59),
                is_active=True,
                is_night_shift=False,
            )
    print(f"Horarios creados para {emp.username}")

# Crear registros de entrada/salida para el período actual
print("Creando registros de asistencia...")


# Función para generar registros de asistencia basados en el horario
def generate_attendance(employee, start_date, days_count=7):
    timers = Timer.objects.filter(employee=employee, is_active=True)

    if not timers.exists():
        print(f"No hay horarios configurados para {employee.username}")
        return

    created_count = 0

    # Para cada día en el rango
    for day_offset in range(days_count):
        current_date = start_date + timedelta(days=day_offset)
        weekday = current_date.weekday()

        # Buscar un timer para ese día de la semana
        day_timer = timers.filter(day=weekday).first()

        if day_timer:
            # Verificar si ya existe un registro para este día
            existing = AttendanceRegister.objects.filter(
                employee=employee, timestamp_in__date=current_date
            ).exists()

            if existing:
                continue

            # Calcular timestamp_in y timestamp_out
            time_in = day_timer.timeIn
            time_out = day_timer.timeOut

            # Manejar caso especial donde el turno termina al día siguiente
            next_day = False
            if time_out < time_in:
                next_day = True

            # Crear datetime con timezone para entrada
            timestamp_in = timezone.make_aware(datetime.combine(current_date, time_in))

            # Crear datetime con timezone para salida
            if next_day:
                timestamp_out = timezone.make_aware(
                    datetime.combine(current_date + timedelta(days=1), time_out)
                )
            else:
                timestamp_out = timezone.make_aware(
                    datetime.combine(current_date, time_out)
                )

            # Introducir pequeñas variaciones
            timestamp_in = timestamp_in + timedelta(minutes=random.randint(-10, 15))
            timestamp_out = timestamp_out + timedelta(minutes=random.randint(-5, 20))

            # Crear registro de asistencia
            AttendanceRegister.objects.create(
                employee=employee,
                timestamp_in=timestamp_in,
                timestamp_out=timestamp_out,
                method=(
                    "fingerprint"
                    if employee.use_finger_print
                    else (
                        "faceId"
                        if employee.face_tamplate
                        else ("pin" if employee.unique_pin else "qr_code")
                    )
                ),
                hash=(
                    employee.fingerprint_hash
                    if employee.use_finger_print
                    else (employee.face_tamplate if employee.face_tamplate else "")
                ),
                paid=False,
                sync=True,
                unique_pin=employee.unique_pin if employee.unique_pin else None,
                qr_code=(
                    employee.qr_code
                    if hasattr(employee, "qr_code") and employee.qr_code
                    else None
                ),
            )
            created_count += 1

    return created_count


# Generar asistencias para los empleados
for emp in employees:
    count = generate_attendance(emp, start_date)
    print(f"Creados {count} registros de asistencia para {emp.username}")

# Crear registro de asistencia abierto para los vacilones
for emp in employees:
    if emp.username in ["tralalero", "tralala"]:
        AttendanceRegister.objects.create(
            employee=emp,
            timestamp_in=timezone.now(),
            timestamp_out=None,
            method="pin",
            hash="",
            paid=False,
            sync=True,
            unique_pin=emp.unique_pin,
        )
        print(f"Registro de asistencia ABIERTO creado para {emp.username}")

print("\nDatos de prueba creados exitosamente!")
print("\nResumen:")
print(f"- Empleados: {len(employees) + 1} (incluyendo admin)")
print(f"- Período de pago activo: {pay_period.description}")
print("- Registros de asistencia creados")
print("\nPuedes acceder al sistema con estos usuarios:")
print("Admin: username=admin, password=admin123")
print("Empleados: username=[maria|juan|carlos], password=password123")
