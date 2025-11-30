# Guía de Implementación: Nueva Funcionalidad de Cierre y Creación de Periodos

## Resumen de Cambios

Se implementó una **nueva acción** en el endpoint de gestión de periodos que ahora maneja automáticamente la migración de entradas actuales (empleados trabajando) del periodo que se cierra al nuevo periodo que se crea.

### Problema que Resuelve

Anteriormente, cuando se cerraba un periodo mientras había empleados trabajando (con `timestamp_in` pero sin `timestamp_out`), esas horas quedaban "atrapadas" en el periodo cerrado y no se contabilizaban correctamente. Ahora, estas entradas se migran automáticamente al nuevo periodo.

---

## Endpoint Actualizado

### `POST /v1/salary/period/`

#### Nueva Acción: `close_and_create_new`

Esta es la acción recomendada para usar de ahora en adelante al cerrar un periodo.

**Request:**
```json
{
  "action": "close_and_create_new",
  "start_date": "2024-12-01",  // Opcional, por defecto: hoy
  "end_date": "2024-12-15"     // Opcional, por defecto: hoy + 15 días
}
```

**Response (201 Created):**
```json
{
  "message": "Período cerrado, nuevo período creado y entradas actuales migradas exitosamente",
  "closed_period": {
    "id": 10,
    "start_date": "2024-11-16",
    "end_date": "2024-11-30",
    "is_closed": true,
    "description": "Quincena 16/11/2024 - 30/11/2024"
  },
  "new_period": {
    "id": 11,
    "start_date": "2024-12-01",
    "end_date": "2024-12-15",
    "is_closed": false,
    "description": "Quincena 01/12/2024 - 15/12/2024"
  },
  "migration": {
    "migrated_count": 5,
    "migrated_employees": [
      {
        "employee_id": 3,
        "employee_username": "maria",
        "timestamp_in": "2024-11-30T20:15:00-06:00"
      },
      {
        "employee_id": 7,
        "employee_username": "carlos",
        "timestamp_in": "2024-11-30T19:30:00-06:00"
      }
    ],
    "message": "Se migraron 5 entradas al nuevo período"
  }
}
```

---

## Lógica de Migración

### ¿Qué entradas se migran?

El sistema identifica automáticamente las entradas que cumplen **TODOS** estos criterios:

1. **Fecha de entrada = HOY** (`timestamp_in` del día actual)
2. **Sin salida** (`timestamp_out` es `null`)
3. **No pagadas** (`paid = false`)

Estas son las personas que están **actualmente trabajando** y cuyas horas pertenecen conceptualmente al nuevo periodo.

### ¿Qué NO se migra?

- Entradas antiguas olvidadas (más de 1 día sin cerrar)
- Entradas ya marcadas como pagadas
- Entradas que ya tienen `timestamp_out`

**Importante:** Si alguien olvidó marcar su salida hace días, esas horas se pierden por contrato (como indica la política de la empresa). La migración solo afecta a los turnos actuales.

---

## Cambios Necesarios en el Frontend

### 1. Actualizar el botón/funcionalidad de "Cerrar Periodo y Crear Nuevo"

**Antes:**
```typescript
// Cerraban en dos pasos
const closePeriod = async () => {
  await fetch('/v1/salary/period/', {
    method: 'POST',
    body: JSON.stringify({ action: 'close_current' })
  });

  await fetch('/v1/salary/period/', {
    method: 'POST',
    body: JSON.stringify({ action: 'create_new', start_date: '...', end_date: '...' })
  });
}
```

**Ahora (RECOMENDADO):**
```typescript
const closePeriodAndCreateNew = async (startDate: string, endDate: string) => {
  const response = await fetch('/v1/salary/period/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'close_and_create_new',
      start_date: startDate,  // Formato: "YYYY-MM-DD" o "DD/MM/YYYY"
      end_date: endDate
    })
  });

  const data = await response.json();

  // Mostrar información de la migración al usuario
  if (data.migration.migrated_count > 0) {
    console.log(`Se migraron ${data.migration.migrated_count} empleados al nuevo periodo`);
    console.log('Empleados migrados:', data.migration.migrated_employees);
  }

  return data;
}
```

### 2. Mostrar información de migración al usuario

Es importante informar al administrador qué empleados fueron migrados:

```typescript
// Ejemplo de notificación
const handleClosePeriod = async () => {
  const result = await closePeriodAndCreateNew('2024-12-01', '2024-12-15');

  if (result.migration.migrated_count > 0) {
    const employeeNames = result.migration.migrated_employees
      .map(e => e.employee_username)
      .join(', ');

    showNotification({
      type: 'info',
      title: 'Periodo cerrado exitosamente',
      message: `${result.migration.migrated_count} empleados actualmente trabajando fueron migrados al nuevo periodo: ${employeeNames}`
    });
  } else {
    showNotification({
      type: 'success',
      message: 'Periodo cerrado y nuevo periodo creado'
    });
  }
}
```

### 3. UI Recomendada

Cuando el usuario haga clic en "Cerrar Periodo y Crear Nuevo", mostrar:

```
┌─────────────────────────────────────────────────┐
│ Cerrar Periodo Actual y Crear Nuevo            │
├─────────────────────────────────────────────────┤
│                                                 │
│ Periodo Actual:                                 │
│ Quincena 16/11/2024 - 30/11/2024               │
│                                                 │
│ Nuevo Periodo:                                  │
│ Fecha Inicio: [2024-12-01]                     │
│ Fecha Fin:    [2024-12-15]                     │
│                                                 │
│ ℹ️  Los empleados actualmente trabajando       │
│    serán migrados automáticamente al nuevo      │
│    periodo.                                     │
│                                                 │
│         [Cancelar]  [Cerrar y Crear]           │
└─────────────────────────────────────────────────┘
```

Después de la operación exitosa:

```
✅ Periodo cerrado exitosamente

Periodo cerrado: Quincena 16/11/2024 - 30/11/2024
Nuevo periodo creado: Quincena 01/12/2024 - 15/12/2024

🔄 Se migraron 5 empleados al nuevo periodo:
   • maria (entrada: 20:15)
   • carlos (entrada: 19:30)
   • jose (entrada: 21:00)
   • ana (entrada: 18:45)
   • pedro (entrada: 22:30)
```

---

## Compatibilidad con Acciones Anteriores

Las acciones antiguas **siguen funcionando** para casos especiales:

### `close_current` (solo cerrar)
```json
{ "action": "close_current" }
```
Cierra el periodo actual sin crear uno nuevo ni migrar entradas.

### `create_new` (solo crear)
```json
{
  "action": "create_new",
  "start_date": "2024-12-01",
  "end_date": "2024-12-15"
}
```
Crea un nuevo periodo (requiere que no haya ninguno abierto).

---

## Casos de Uso y Escenarios

### Escenario 1: Cierre Normal (hay empleados trabajando)
- **Situación:** Es día de cierre (30/11) a las 10 AM, hay 5 empleados que entraron hoy pero no han salido
- **Acción:** `close_and_create_new`
- **Resultado:** Esos 5 empleados son migrados al nuevo periodo automáticamente
- **Beneficio:** Sus horas se contarán en el periodo correcto cuando marquen salida

### Escenario 2: Cierre con entradas olvidadas
- **Situación:** Un empleado olvidó marcar salida hace 3 días
- **Acción:** `close_and_create_new`
- **Resultado:** Esa entrada NO se migra (solo se migran las de HOY)
- **Beneficio:** Se respeta la política de que entradas olvidadas se pierden

### Escenario 3: Cierre sin empleados trabajando
- **Situación:** Es día de cierre pero nadie está trabajando en este momento
- **Acción:** `close_and_create_new`
- **Resultado:** Se cierra el periodo y se crea uno nuevo, `migrated_count = 0`
- **Beneficio:** Funciona igual, sin migración

---

## Testing Recomendado

### Tests del Frontend

1. **Test: Cerrar periodo con empleados trabajando**
   - Crear entradas sin salida para hoy
   - Ejecutar `close_and_create_new`
   - Verificar que la respuesta incluya `migration.migrated_count > 0`
   - Verificar que los empleados listados sean los correctos

2. **Test: Cerrar periodo sin empleados trabajando**
   - No crear entradas para hoy
   - Ejecutar `close_and_create_new`
   - Verificar que `migration.migrated_count = 0`

3. **Test: Validar fechas del nuevo periodo**
   - Ejecutar con fechas personalizadas
   - Verificar que el nuevo periodo tenga las fechas correctas

---

## Errores Posibles

### Error 400: "No hay un período de pago abierto para cerrar"
**Causa:** No existe un periodo activo (todos están cerrados)
**Solución:** Primero crear un periodo con `create_new`, luego usar `close_and_create_new`

### Error 400: "Acción no válida"
**Causa:** El valor de `action` no es válido
**Solución:** Usar uno de: `close_current`, `create_new`, `close_and_create_new`

---

## Migración Gradual

Pueden migrar gradualmente:

1. **Fase 1 (Inmediata):** Actualizar el backend (ya hecho ✅)
2. **Fase 2 (Esta semana):** Actualizar el frontend para usar `close_and_create_new`
3. **Fase 3 (Futuro):** Remover las acciones antiguas si ya no se usan

Por ahora, **ambos métodos funcionan**, así que no hay prisa en actualizar el frontend, pero se recomienda hacerlo pronto.

---

## Resumen para el Desarrollador Frontend

**Cambio mínimo necesario:**

```diff
- action: 'close_current'
- // luego
- action: 'create_new'
+ action: 'close_and_create_new'
```

**Beneficio:**
- Una sola llamada en lugar de dos
- Migración automática de empleados trabajando
- Respuesta con información detallada de la migración

**Acción recomendada:**
Actualizar el botón de "Cerrar Periodo" para usar la nueva acción `close_and_create_new` y mostrar la información de migración al usuario.
