# Guía de Integración Frontend - Sistema de Planilla

Este documento detalla cómo implementar el frontend para la app de tablet que se integrará con la API del Sistema de Marcaje y Planilla del Hospital Veterinario. La aplicación estará instalada únicamente en un dispositivo en la entrada del hospital para marcajes biométricos.

## Tecnología Base

- **Framework:** React Native con Expo
- **Autenticación:** JWT para los administradores
- **UI/Componentes:** React Native Paper o Native Base
- **API Calls:** Axios
- **Almacenamiento local:** AsyncStorage para el token de administrador

## Endpoints Principales

### Autenticación

**Endpoint:** `POST /v1/auth/`

- **Caso de uso:** Login exclusivo para administradores mediante huella digital o reconocimiento facial
- **Request Body:**
  ```json
  {
    "method": "fingerprint",
    "hash": "admin_hash_value"
  }
  ```
- **Response:** Token JWT que deberá guardarse para autenticar las operaciones administrativas
- **Implementación frontend:** Pantalla de login accesible solo desde un modo administrador protegido

### Empleados

**Endpoint:** `GET /v1/employee/`

- **Caso de uso:** Listar todos los empleados (solo para administradores)
- **Headers:** `Authorization: Bearer <token_jwt>`
- **Implementación frontend:** Tabla de empleados con opciones de filtrado en modo administrador

**Endpoint:** `POST /v1/employee/`

- **Caso de uso:** Crear nuevo empleado (solo para administradores)
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
    "use_finger_print": true,
    "fingerprint_hash": "juan_finger_hash"
  }
  ```
- **Implementación frontend:** Formulario dentro del modo administrador

### Asistencia

**Endpoint:** `POST /v1/attendance/in/`

- **Caso de uso:** Marcaje de entrada (pantalla principal de la tablet)
- **Request Body:**
  ```json
  {
    "method": "fingerprint",
    "hash": "juan_finger_hash"
  }
  ```
- **Implementación frontend:**
  - Pantalla principal con botón prominente "Marcar Entrada"
  - Lector de huella digital integrado
  - Confirmación visual de marcaje exitoso
  - Sin necesidad de login para el empleado

**Endpoint:** `POST /v1/attendance/out/`

- **Caso de uso:** Marcaje de salida (pantalla principal de la tablet)
- **Request Body:**
  ```json
  {
    "method": "fingerprint",
    "hash": "juan_finger_hash"
  }
  ```
- **Implementación frontend:**
  - Botón "Marcar Salida" en pantalla principal
  - Confirmación visual de marcaje exitoso
  - **Mostrar horas trabajadas del día al marcar salida**
  - Sin necesidad de login para el empleado

### Horarios (Solo Administradores)

**Endpoint:** `GET /v1/timer/<employee_id>/timers/`

- **Caso de uso:** Ver horarios configurados de un empleado
- **Headers:** `Authorization: Bearer <token_jwt>`
- **Implementación frontend:** Tabla en el modo administrativo

**Endpoint:** `POST /v1/timer/`

- **Caso de uso:** Configurar horario para empleado
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
- **Implementación frontend:** Formulario en el modo administrativo

### Períodos de Pago (Solo Administradores)

**Endpoint:** `POST /v1/salary/period/`

- **Caso de uso:** Crear o cerrar períodos de pago
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
- **Implementación frontend:** Botones en el panel de administración

**Endpoint:** `GET /v1/salary/night-hours/?period_id=X`

- **Caso de uso:** Listar empleados con horas nocturnas para un período
- **Headers:** `Authorization: Bearer <token_jwt>`
- **Implementación frontend:** Tabla con checkbox en el modo administrativo

**Endpoint:** `POST /v1/salary/calculate/`

- **Caso de uso:** Calcular salario de un empleado para un período
- **Headers:** `Authorization: Bearer <token_jwt>`
- **Request Body:**
  ```json
  {
    "employee_id": 2,
    "apply_night_factor": true,
    "period_id": 1
  }
  ```
- **Implementación frontend:** Botón "Calcular" junto a cada empleado en el modo administrativo

## Estructura de la Aplicación

### 1. Modo Marcaje (Pantalla Principal)

Esta será la interfaz predeterminada para la tablet en la entrada del hospital:

- **Pantalla simple con dos botones grandes:**
  - "Marcar Entrada"
  - "Marcar Salida"
- **Flujo de Marcaje:**
  1. El empleado selecciona el tipo de marcaje (entrada/salida)
  2. Se solicita huella digital
  3. Se muestra confirmación o error
  4. Al marcar salida, se muestra un resumen de horas trabajadas ese día
  5. La pantalla vuelve automáticamente al modo inicial después de un tiempo de inactividad

### 2. Modo Administrador (Acceso Protegido)

Este modo debe estar protegido y solo accesible mediante un gesto específico seguido de autenticación:

- **Gestión de Empleados:**

  - Lista de empleados con filtros
  - Formulario para crear/editar empleados
  - Gestión de horarios por empleado

- **Gestión de Períodos:**

  - Lista de períodos (activos/cerrados)
  - Botones para crear/cerrar períodos
  - Vista de cálculos por período

- **Cálculo de Planilla:**
  - Selección de período
  - Lista de empleados con horas trabajadas
  - Opción para aplicar factor nocturno individualmente
  - Resumen de planilla total

## Consideraciones de Diseño

1. **Interfaz para Tablet:**

   - Botones grandes y fáciles de tocar
   - Texto legible desde distancia razonable
   - Colores contrastantes y claros

2. **Modo Nocturno:**

   - Implementar modo oscuro automático durante la noche
   - Reducir brillo para no molestar en turnos nocturnos

3. **Alertas y Confirmaciones:**

   - Confirmaciones visuales claras para marcajes exitosos
   - Sonidos distintivos (pero discretos) para confirmación
   - Mensajes de error descriptivos cuando falle la autenticación

4. **Seguridad:**
   - Acceso al modo administrador no obvio (gesto específico + autenticación)
   - Timeout automático para volver al modo marcaje
   - Bloqueo temporal después de varios intentos fallidos

## Validaciones Importantes

1. **Marcaje de Entrada/Salida:**

   - No permitir marcar salida sin entrada previa
   - Mostrar información del empleado al marcar (nombre, foto si disponible)
   - Mostrar horas trabajadas al marcar salida

2. **Administración:**
   - Confirmar acciones destructivas o importantes
   - Validar todos los formularios antes de enviar
   - Mostrar progreso en operaciones largas

## Documentación de la API

La documentación completa de la API está disponible en el esquema OpenAPI/Swagger accesible desde la ruta `/api/schema/swagger-ui/` del backend.

## Consideraciones para Desarrollo con Expo

- Usar Expo SDK para acceder a funcionalidades nativas como cámara y lector de huella
- Considerar EAS (Expo Application Services) para builds y actualizaciones
- Implementar estrategia de caché para funcionamiento offline básico
- Optimizar el uso de recursos para evitar bloqueos en la tablet
