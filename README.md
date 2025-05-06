# Sistema de Marcaje y Planilla para Hospital Veterinario

API REST para el registro de asistencia de empleados, cálculo de horas trabajadas y generación de planillas.

## Características Principales

- Marcaje de entrada/salida mediante huella digital o reconocimiento facial
- Cálculo automático de horas trabajadas (regulares y extras)
- Soporte para turnos nocturnos con factor de pago personalizable
- Administración de períodos de pago quincenales
- Notificaciones automáticas por WhatsApp
- Recordatorios automáticos de cierre de quincena a administradores
- Cálculo automático de salarios

## Configuración

### Requisitos

- Python 3.12+
- Django 5.1+
- PostgreSQL/SQLite
- Redis (para Celery)

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/payroll-system-api.git
cd payroll-system-api

# Crear entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar archivo .env con tus credenciales

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor
python manage.py runserver
```

### Variables de Entorno Requeridas

```
# Django
SECRET_KEY=your_secret_key
DEBUG=True

# Twilio (Notificaciones WhatsApp)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=your_twilio_whatsapp_number
TWILIO_MESSAGE_TEMPLATE_ID=your_template_id_for_attendance_notifications
TWILIO_MESSAGE_TEMPLATE_ID_2=your_template_id_for_admin_reminders

# Base de Datos (opcional si se usa SQLite)
DB_NAME=payroll_db
DB_USER=username
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
```

## Flujo de Trabajo Completo

### 1. Inicio

1. **Crear un período de pago:**

   ```bash
   POST /v1/salary/period/
   Content-Type: application/json
   Authorization: Bearer <tu_token>

   {
     "action": "create_new",
     "start_date": "2023-06-01",
     "end_date": "2023-06-15"
   }
   ```

2. **Crear empleado administrador:**

   ```bash
   POST /v1/employee/
   Content-Type: application/json

   {
     "username": "admin1",
     "first_name": "Admin",
     "last_name": "User",
     "password": "securepassword",
     "is_admin": true,
     "salary_hour": 20.00,
     "biweekly_hours": 96.0,
     "night_shift_factor": 1.0,
     "phone": "+50688887777",
     "use_finger_print": true,
     "fingerprint_hash": "sample_hash_123"
   }
   ```

3. **Autenticarse como admin:**

   ```bash
   POST /v1/auth/
   Content-Type: application/json

   {
     "fingerprint": "sample_hash_123"
   }
   ```

   Esto te dará un token JWT que necesitarás para operaciones administrativas.

### 2. Configuración del Sistema

1. **Crear empleados regulares:**

   ```bash
   POST /v1/employee/
   Content-Type: application/json
   Authorization: Bearer <tu_token>

   {
     "username": "juan",
     "first_name": "Juan",
     "last_name": "Médico",
     "password": "juan123",
     "is_admin": false,
     "salary_hour": 15.00,
     "biweekly_hours": 96.0,
     "night_shift_factor": 1.2,
     "phone": "+50688886666",
     "use_finger_print": true,
     "fingerprint_hash": "juan_finger_hash"
   }
   ```

2. **Configurar horarios para empleados:**
   Para turnos diurnos:

   ```bash
   POST /v1/timer/
   Content-Type: application/json
   Authorization: Bearer <tu_token>

   {
     "employee": 2,
     "day": 1,  # 0=Domingo, 1=Lunes, etc.
     "timeIn": "08:00:00",
     "timeOut": "17:00:00",
     "is_active": true,
     "is_night_shift": false
   }
   ```

   Para turnos nocturnos:

   ```bash
   POST /v1/timer/
   Content-Type: application/json
   Authorization: Bearer <tu_token>

   {
     "employee": 2,
     "day": 3,  # 0=Domingo, 1=Lunes, etc.
     "timeIn": "21:00:00",
     "timeOut": "06:00:00",
     "is_active": true,
     "is_night_shift": true
   }
   ```

3. **Verificar horarios configurados:**
   ```bash
   GET /v1/timer/<employee_id>/timers/
   Authorization: Bearer <tu_token>
   ```

### 3. Operación Diaria

1. **Marcaje de entrada:**

   ```bash
   POST /v1/attendance/in/
   Content-Type: application/json

   {
     "method": "fingerprint",
     "hash": "juan_finger_hash"
   }
   ```

2. **Marcaje de salida:**

   ```bash
   POST /v1/attendance/out/
   Content-Type: application/json

   {
     "method": "fingerprint",
     "hash": "juan_finger_hash"
   }
   ```

### 4. Cierre de Período y Cálculo de Pago

1. **Cerrar período actual:**

   ```bash
   POST /v1/salary/period/
   Content-Type: application/json
   Authorization: Bearer <tu_token>

   {
     "action": "close_current"
   }
   ```

2. **Crear nuevo período:**

   ```bash
   POST /v1/salary/period/
   Content-Type: application/json
   Authorization: Bearer <tu_token>

   {
     "action": "create_new"
   }
   ```

3. **Verificar empleados con horas nocturnas** en el período recién cerrado:

   ```bash
   GET /v1/salary/night-hours/?period_id=X
   Authorization: Bearer <tu_token>
   ```

   Esto devolverá una lista de empleados con horas nocturnas en el período cerrado.

4. **Calcular salario para cada empleado:**

   ```bash
   POST /v1/salary/calculate/
   Content-Type: application/json
   Authorization: Bearer <tu_token>

   {
     "employee_id": 2,
     "apply_night_factor": true,
     "period_id": X
   }
   ```

## Cálculo de Horas y Salario

El sistema funciona de la siguiente manera:

1. Cada empleado tiene configurado:

   - Un salario por hora (`salary_hour`)
   - Un máximo de horas quincenales (`biweekly_hours`, por defecto 96)
   - Un factor de pago nocturno (`night_shift_factor`, 1.0 para normal, 1.2 para 20% extra)

2. Horarios y turnos:

   - Se configura un horario (timeIn, timeOut) por cada día de la semana
   - Los turnos pueden marcarse como nocturnos (`is_night_shift=true`)
   - También se detectan automáticamente como nocturnos si caen entre 7pm y 6am

3. Cálculo de horas:

   - **Horas regulares**: Hasta el límite quincenal configurado (default 96 horas)
   - **Horas extras**: Todas las que excedan el límite quincenal
   - **Horas nocturnas**: Las trabajadas en turnos nocturnos (dentro de las regulares)

4. Cálculo de salario:
   - **Pago regular**: Horas regulares × Salario por hora
   - **Pago nocturno**: Horas nocturnas × Salario por hora × (Factor nocturno - 1)
   - **Pago extra**: Horas extras × Salario por hora × 1.5

## Notificaciones

### Notificaciones para Empleados

El sistema envía notificaciones automáticas por WhatsApp cuando:

- Un empleado no marca entrada en su horario programado
- Un empleado no marca salida después de su horario

### Recordatorios a Administradores

El sistema envía recordatorios automáticos por WhatsApp a los administradores:

- Los días 14 y 28 de cada mes (recordatorio de cierre de quincena)
- El mensaje se envía a todos los usuarios con `is_admin=True`
- Requiere configurar la variable `TWILIO_MESSAGE_TEMPLATE_ID_2` en las variables de entorno

Para que esta función opere correctamente:

- Asegurarse de que los administradores tengan número de teléfono registrado
- Verificar que las fechas en el código (`payrolls/tasks.py`) y en la programación (`settings.py`) sean consistentes
- Todos los administradores deben tener el flag `is_admin=True` en su perfil

## Soporte

Para soporte técnico, contactar a: soporte@example.com
