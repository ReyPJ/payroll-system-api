# 🚨 Solución para Cálculo de Salarios Temprano

## Problema Identificado

Se calcularon salarios el **28/11/2024** para el período **15/11 - 30/11**, cuando aún faltaban 2 días para el fin del período. Esto afectó a **3 empleados**.

### ¿Qué Pasó?

1. El sistema procesó asistencias del 15/11 al 28/11 (14 días)
2. Marcó esas asistencias como `paid=True` en la base de datos
3. Creó registros de salario con horas parciales

### ¿Qué Pasará si Recalculan Sin Arreglar?

- ❌ El sistema **SOLO** verá asistencias del 29/11 y 30/11 (porque busca `paid=False`)
- ❌ El registro de salario se **REEMPLAZARÁ** (no se sumará)
- ❌ **LOS EMPLEADOS PERDERÁN las horas del 15/11 al 28/11**
- ❌ Solo se les pagarán 2 días en lugar de 16 días completos

### Ejemplo del Impacto:

```
Cálculo del 28/11:
├─ Horas: 112 horas (14 días × 8 horas)
└─ Salario: $1,120

Si recalculan el 30/11 SIN ARREGLAR:
├─ Horas: 16 horas (2 días × 8 horas) ❌
├─ Salario: $160 ❌
└─ PÉRDIDA: $960 ❌
```

---

## ✅ SOLUCIÓN INMEDIATA (Para los 3 Empleados Afectados)

### 🚂 Para Proyectos en RAILWAY (Más Fácil - USA ESTO)

Si tu proyecto está en Railway, usa el **endpoint de API** que creamos. No necesitas CLI:

#### Paso 1: Identificar IDs (Usa tu admin de Django o base de datos)

Necesitas saber:
- ID del período 15/11-30/11
- IDs de los 3 empleados afectados

#### Paso 2: Hacer Dry-Run (Ver qué se hará)

```bash
POST https://tu-app.railway.app/payrolls/admin/reset-attendance/
Authorization: Bearer TU_TOKEN
Content-Type: application/json

{
  "period_id": 5,
  "employee_ids": [10, 15, 20],
  "delete_salary_records": true,
  "dry_run": true
}
```

#### Paso 3: Ejecutar la Corrección Real

Si el dry-run se ve bien, ejecuta sin `dry_run`:

```bash
POST https://tu-app.railway.app/payrolls/admin/reset-attendance/
Authorization: Bearer TU_TOKEN
Content-Type: application/json

{
  "period_id": 5,
  "employee_ids": [10, 15, 20],
  "delete_salary_records": true,
  "dry_run": false
}
```

**Respuesta esperada:**
```json
{
  "message": "Operación completada exitosamente",
  "dry_run": false,
  "period": {
    "id": 5,
    "description": "Quincena 15/11/2024 - 30/11/2024"
  },
  "summary": {
    "employees_processed": 3,
    "attendance_reset": 42,
    "details_deleted": 42,
    "salary_records_deleted": 3
  },
  "next_steps": [
    "Los empleados están listos para recalcular",
    "Usa POST /payrolls/calculate/ para recalcular"
  ]
}
```

---

### 💻 Para Proyectos LOCALES o con Railway CLI

#### Opción 1: Identificar el ID del Período

Primero, necesitas saber el ID del período de pago 15/11 - 30/11:

```bash
# Con Railway CLI
railway run python manage.py shell

# O localmente
python manage.py shell

# Buscar el período
from payrolls.models import PayPeriod
period = PayPeriod.objects.filter(
    start_date__lte='2024-11-30',
    end_date__gte='2024-11-30'
).first()
print(f"ID del período: {period.id}")
print(f"Descripción: {period.description}")
exit()
```

#### Opción 2: Resetear las Asistencias

Una vez que tengas el ID del período (supongamos que es `5`) y los IDs de los 3 empleados afectados (supongamos `10, 15, 20`):

#### Paso 1: Hacer una prueba (dry-run) para ver qué se hará

```bash
python manage.py reset_attendance_paid_status \
  --period-id=5 \
  --employees 10 15 20 \
  --delete-salary-records \
  --dry-run
```

Este comando mostrará:
- Cuántas asistencias se resetearán
- Cuántos detalles se eliminarán
- Si hay registros de salario para eliminar
- **NO HARÁ CAMBIOS REALES**

#### Paso 2: Ejecutar la corrección real

Si todo se ve correcto en el dry-run, ejecuta sin el flag `--dry-run`:

```bash
python manage.py reset_attendance_paid_status \
  --period-id=5 \
  --employees 10 15 20 \
  --delete-salary-records
```

Este comando:
- ✅ Reseteará todas las asistencias a `paid=False`
- ✅ Eliminará los detalles de asistencia calculados incorrectamente
- ✅ Eliminará los registros de salario parciales
- ✅ Dejará todo listo para recalcular correctamente

#### Paso 3: Recalcular los Salarios Correctamente

Ahora puedes recalcular los salarios normalmente el **30/11** usando tu API:

```bash
POST /payrolls/calculate/
{
  "employee_id": 10,
  "period_id": 5,
  "apply_night_factor": true
}
```

O calcular todos a la vez:

```bash
GET /payrolls/calculate-all/?period_id=5&apply_night_factor=true
```

---

## 🛡️ PREVENCIÓN: Cambios Implementados

### 1. Advertencias Automáticas

Ahora el sistema mostrará advertencias cuando:

**a) Se calcula antes del fin del período:**

```json
{
  "salary_record": { ... },
  "warnings": [
    {
      "type": "early_calculation",
      "message": "⚠️ ADVERTENCIA: Estás calculando el salario 2 día(s) antes del fin del período (30/11/2024)",
      "details": "Si el empleado sigue trabajando, tendrás que recalcular usando el comando 'reset_attendance_paid_status'",
      "days_remaining": 2,
      "period_end_date": "2024-11-30"
    }
  ]
}
```

**b) Se recalcula un salario existente:**

```json
{
  "salary_record": { ... },
  "warnings": [
    {
      "type": "recalculation",
      "message": "⚠️ Ya existe un cálculo previo para este empleado en este período",
      "details": "Tienes 14 registros de asistencia ya marcados como pagados. El cálculo se actualizará pero solo con registros nuevos no pagados.",
      "previous_calculation_date": "2024-11-28T10:30:00Z",
      "previous_total_hours": "112.00",
      "previous_salary": "1120.00"
    }
  ]
}
```

### 2. Comando de Management para Correcciones

Se creó el comando `reset_attendance_paid_status` para manejar situaciones como esta.

---

## 📋 MEJORES PRÁCTICAS

### ✅ Cuándo Calcular Salarios

1. **Esperar hasta el fin del período** (30/11, 15/11, etc.)
2. Verificar que todos los empleados hayan registrado su salida
3. Revisar que no haya errores de marcación

### ✅ Antes de Calcular

```bash
# Ver empleados con asistencias pendientes
GET /payrolls/employees-night-hours/?period_id=5

# Verificar período activo
GET /payrolls/period/?is_active=true
```

### ✅ Si Necesitas Calcular Antes de Tiempo

Solo en casos excepcionales (emergencia, empleado se va, etc.):

1. **Anota** qué empleados calculaste temprano
2. **Espera** las advertencias del sistema
3. **Prepárate** para recalcular usando el comando de reset
4. **No calcules** a todos los empleados antes de tiempo

### ❌ Nunca Hagas Esto

- ❌ Calcular toda la planilla días antes del fin del período
- ❌ Ignorar las advertencias del sistema
- ❌ Recalcular sin resetear las asistencias primero
- ❌ Modificar manualmente el flag `paid` en la base de datos

---

## 🔧 Uso Avanzado del Comando

### Resetear Todos los Empleados de un Período

```bash
python manage.py reset_attendance_paid_status \
  --period-id=5 \
  --all-employees \
  --delete-salary-records
```

### Solo Resetear Asistencias (Mantener Registros de Salario)

Útil si solo quieres agregar horas nuevas sin eliminar el cálculo anterior:

```bash
python manage.py reset_attendance_paid_status \
  --period-id=5 \
  --employees 10 15 20
```

**NOTA:** Esto NO se recomienda porque el registro de salario se reemplazará con solo las nuevas horas.

### Ver Ayuda del Comando

```bash
python manage.py reset_attendance_paid_status --help
```

---

## 🆘 Soporte

Si tienes problemas:

1. Ejecuta el comando con `--dry-run` primero
2. Revisa los warnings del sistema
3. Verifica los IDs de empleados y períodos
4. Si algo falla, contacta al equipo de desarrollo

---

## 📝 Resumen de Archivos Modificados

### Nuevos Archivos

- `payrolls/management/commands/reset_attendance_paid_status.py` - Comando para resetear asistencias

### Archivos Modificados

- `payrolls/views.py` - Agregadas validaciones y advertencias en:
  - `CalculateSalary.post()` - Cálculo individual
  - `CalculateAllSalaries.get()` - Cálculo masivo

### Cómo Funciona la Validación

```python
# En payrolls/views.py líneas 65-99
if today < pay_period.end_date:
    # Advertencia de cálculo temprano
    warnings.append({...})

if salary_record:
    # Advertencia de recálculo
    warnings.append({...})
```

---

## 🎯 Acción Inmediata para tu Caso (RAILWAY)

### Opción A: Usando el Endpoint de API (Recomendado)

**1. Identifica los IDs desde tu admin de Django o base de datos**
   - Ve a: https://tu-app.railway.app/admin/payrolls/payperiod/
   - Busca el período "15/11/2024 - 30/11/2024"
   - Anota el ID del período

   - Ve a: https://tu-app.railway.app/admin/payrolls/salaryrecord/
   - Filtra por el período
   - Anota los IDs de los 3 empleados afectados

**2. Usa Postman, Thunder Client o curl para hacer el dry-run**

```bash
curl -X POST https://tu-app.railway.app/payrolls/admin/reset-attendance/ \
  -H "Authorization: Bearer TU_TOKEN_DE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "period_id": [ID_DEL_PERIODO],
    "employee_ids": [[ID1], [ID2], [ID3]],
    "delete_salary_records": true,
    "dry_run": true
  }'
```

**3. Si se ve bien, ejecuta sin dry_run**

```bash
curl -X POST https://tu-app.railway.app/payrolls/admin/reset-attendance/ \
  -H "Authorization: Bearer TU_TOKEN_DE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "period_id": [ID_DEL_PERIODO],
    "employee_ids": [[ID1], [ID2], [ID3]],
    "delete_salary_records": true,
    "dry_run": false
  }'
```

**4. Recalcula los salarios normalmente**
   - Usa tu API de cálculo como siempre

---

### Opción B: Usando Railway CLI

```bash
# 1. Identificar el ID del período 15/11-30/11
railway run python manage.py shell
>>> from payrolls.models import PayPeriod
>>> period = PayPeriod.objects.filter(description__contains="15/11").first()
>>> print(f"ID: {period.id}")
>>> exit()

# 2. Identificar IDs de los 3 empleados afectados
# (Ya debes conocerlos)

# 3. Hacer dry-run
railway run python manage.py reset_attendance_paid_status \
  --period-id=[ID_DEL_PERIODO] \
  --employees [ID1] [ID2] [ID3] \
  --delete-salary-records \
  --dry-run

# 4. Si todo se ve bien, ejecutar sin --dry-run
railway run python manage.py reset_attendance_paid_status \
  --period-id=[ID_DEL_PERIODO] \
  --employees [ID1] [ID2] [ID3] \
  --delete-salary-records

# 5. Recalcular salarios correctamente
# Usar tu API normal de cálculo de salarios
```

---

**Fecha de creación:** 29 de noviembre de 2024
**Versión:** 1.0
