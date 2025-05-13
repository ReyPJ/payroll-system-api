# Documentación de Endpoints - Sistema de Planilla

## Endpoints de Autenticación

**Endpoint:** `POST /v1/auth/`

- **Request Body:**
  ```json
  {
    "unique_pin": "1234"
  }
  ```
- **Response:**
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "username": "admin",
    "is_admin": true
  }
  ```

## Endpoints de NFC Token

**Endpoint:** `POST /v1/auth/nfc/create/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Request Body:**
  ```json
  {
    "employee_id": 2,
    "tag_id": "ABC123XYZ"
  }
  ```
- **Response:**
  ```json
  {
    "id": 1,
    "employee": 2,
    "tag_id": "ABC123XYZ",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "revoked": false,
    "created_at": "2025-05-10T14:30:00Z"
  }
  ```

**Endpoint:** `POST /v1/auth/nfc/validate/`

- **Request Body:**
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response:** (información del payload)
  ```json
  {
    "employee_id": 2,
    "tag_id": "ABC123XYZ",
    "exp": 1620000000,
    "iat": 1588464000
  }
  ```

**Endpoint:** `POST /v1/auth/nfc/revoke/<id>/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Response:**
  ```json
  {
    "message": "Token NFC revocado exitosamente"
  }
  ```

## Endpoints de Empleados

**Endpoint:** `GET /v1/employee/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Response:**
  ```json
  [
    {
      "id": 1,
      "username": "admin",
      "first_name": "Admin",
      "last_name": "Usuario",
      "is_admin": true,
      "salary_hour": 25.0,
      "biweekly_hours": 96.0,
      "night_shift_factor": 1.0,
      "phone": "",
      "unique_pin": "1234"
    }
  ]
  ```

**Endpoint:** `POST /v1/employee/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Request Body:**
  ```json
  {
    "username": "juan",
    "first_name": "Juan",
    "last_name": "Médico",
    "password": "juan123",
    "is_admin": false,
    "salary_hour": 15.0,
    "biweekly_hours": 96.0,
    "night_shift_factor": 1.2,
    "phone": "+50688886666",
    "unique_pin": "1234"
  }
  ```
- **Response:** Objeto empleado creado

## Endpoints de Asistencia

**Endpoint:** `POST /v1/attendance/in/`

- **Request Body:**
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response:**
  ```json
  [
    {
      "message": "Entrada registrada exitosamente para juan"
    },
    {
      "employee_name": "Juan Médico"
    }
  ]
  ```

**Endpoint:** `POST /v1/attendance/out/`

- **Request Body:**
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response:**
  ```json
  [
    {
      "message": "Salida registrada exitosamente para juan"
    },
    {
      "employee_name": "Juan Médico"
    }
  ]
  ```

## Endpoints de Horarios

**Endpoint:** `GET /v1/timer/<employee_id>/timers/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Response:**
  ```json
  [
    {
      "id": 1,
      "employee": 2,
      "day": 1,
      "timeIn": "08:00:00",
      "timeOut": "17:00:00",
      "is_active": true,
      "is_night_shift": false
    }
  ]
  ```

**Endpoint:** `POST /v1/timer/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Request Body:**
  ```json
  {
    "employee": 2,
    "day": 1,
    "timeIn": "08:00:00",
    "timeOut": "17:00:00",
    "is_active": true,
    "is_night_shift": false
  }
  ```
- **Response:** Objeto timer creado

## Endpoints de Períodos de Pago

**Endpoint:** `GET /v1/salary/period/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Parámetros opcionales:** `period_id`, `is_active` (true/false)
- **Response:**
  ```json
  [
    {
      "id": 2,
      "start_date": "2023-07-01",
      "end_date": "2023-07-15",
      "is_closed": false,
      "description": "Quincena 2023-07-01 - 2023-07-15"
    }
  ]
  ```

**Endpoint:** `POST /v1/salary/period/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Request Body para crear período:**
  ```json
  {
    "action": "create_new",
    "start_date": "2023-06-01",
    "end_date": "2023-06-15"
  }
  ```
- **Request Body para cerrar período:**
  ```json
  {
    "action": "close_current"
  }
  ```
- **Response:** Objeto período creado/modificado

## Endpoints de Horas Nocturnas

**Endpoint:** `GET /v1/salary/night-hours/?period_id=X`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Response:**
  ```json
  [
    {
      "id": 2,
      "username": "juan",
      "full_name": "Juan Médico",
      "night_hours": 8.5,
      "night_shift_factor": 1.2,
      "period": {
        "id": 1,
        "description": "Quincena 2023-06-01 - 2023-06-15"
      }
    }
  ]
  ```

## Endpoints de Cálculo de Salarios

**Endpoint:** `POST /v1/salary/calculate/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Request Body:**
  ```json
  {
    "employee_id": 2,
    "apply_night_factor": true,
    "period_id": 1,
    "lunch_deduction_hours": 5.0,
    "other_deductions": 20.0,
    "other_deductions_description": "Adelanto de salario"
  }
  ```
- **Response:**
  ```json
  {
    "id": 1,
    "employee": 2,
    "employee_name": "Juan Médico",
    "total_hours": 85.0,
    "regular_hours": 80.0,
    "night_hours": 8.5,
    "extra_hours": 5.0,
    "night_shift_factor_applied": 1.2,
    "gross_salary": 1500.0,
    "lunch_deduction_hours": 5.0,
    "other_deductions": 20.0,
    "other_deductions_description": "Adelanto de salario",
    "salary_to_pay": 1455.0,
    "paid_at": "2023-06-16T10:30:45Z",
    "sync": false,
    "pay_period": 1,
    "period_name": "Quincena 2023-06-01 - 2023-06-15",
    "has_night_hours": true
  }
  ```

**Endpoint:** `GET /v1/salary/calculate-all/?period_id=X&apply_night_factor=true&lunch_deduction_hours=5&other_deductions=0&other_deductions_description=`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Response:**
  ```json
  {
    "message": "Cálculo de planilla completado",
    "records": [
      {
        "id": 1,
        "employee": 2,
        "employee_name": "Juan Médico",
        "total_hours": 85.0,
        "regular_hours": 80.0,
        "night_hours": 8.5,
        "extra_hours": 5.0,
        "night_shift_factor_applied": 1.2,
        "gross_salary": 1500.0,
        "lunch_deduction_hours": 5.0,
        "other_deductions": 0.0,
        "other_deductions_description": "",
        "salary_to_pay": 1455.0,
        "paid_at": "2023-06-16T10:30:45Z",
        "pay_period": 1,
        "period_name": "Quincena 2023-06-01 - 2023-06-15",
        "has_night_hours": true
      }
    ],
    "total_planilla": 1455.0,
    "empleados_procesados": 1
  }
  ```

## Endpoints de Registros de Salarios

**Endpoint:** `GET /v1/salary/records/?period_id=X`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Response:**
  ```json
  [
    {
      "id": 1,
      "employee": 2,
      "employee_name": "Juan Médico",
      "total_hours": 85.0,
      "regular_hours": 80.0,
      "night_hours": 8.5,
      "extra_hours": 5.0,
      "night_shift_factor_applied": 1.2,
      "gross_salary": 1500.0,
      "lunch_deduction_hours": 5.0,
      "other_deductions": 20.0,
      "other_deductions_description": "Adelanto de salario",
      "salary_to_pay": 1455.0,
      "paid_at": "2023-06-16T10:30:45Z",
      "sync": false,
      "pay_period": 1,
      "period_name": "Quincena 2023-06-01 - 2023-06-15",
      "has_night_hours": true
    }
  ]
  ```

**Endpoint:** `GET /v1/salary/records/<id>/`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Response:** Objeto registro de salario detallado (igual formato que arriba)

## Endpoints de Detalles de Asistencia

**Endpoint:** `GET /v1/salary/attendance-details/?employee_id=X&period_id=Y`

- **Headers:** `Authorization: Bearer <token_jwt>`
- **Response:**
  ```json
  [
    {
      "id": 1,
      "employee": 2,
      "employee_name": "Juan Médico",
      "pay_period": 1,
      "work_date": "2023-06-01",
      "formatted_date": "01/06/2023",
      "time_in": "08:00:00",
      "time_out": "17:00:00",
      "regular_hours": 8.0,
      "night_hours": 0.0,
      "extra_hours": 1.0,
      "lunch_deduction": 1.0
    }
  ]
  ```
