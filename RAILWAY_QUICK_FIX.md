# 🚂 Solución Rápida para Railway - Cálculo Temprano de Salarios

## 🚨 El Problema
Se calcularon salarios el 28/11 en vez del 30/11, afectando a 3 empleados. Si recalculas sin arreglar, **perderán las horas del 15-28 de noviembre**.

---

## ✅ Solución Usando el Endpoint de API

### Paso 1: Obtén los IDs necesarios

**ID del Período:**
1. Ve a tu admin de Django: `https://tu-app.railway.app/admin/payrolls/payperiod/`
2. Busca "Quincena 15/11/2024 - 30/11/2024"
3. Anota el **ID** (ejemplo: `5`)

**IDs de los Empleados:**
1. Ve a: `https://tu-app.railway.app/admin/payrolls/salaryrecord/`
2. Filtra por el período de 15/11-30/11
3. Anota los **IDs de los 3 empleados** afectados (ejemplo: `10, 15, 20`)

---

### Paso 2: Prueba Primero (Dry-Run)

Usa **Postman**, **Thunder Client**, o **curl**:

```bash
POST https://tu-app.railway.app/payrolls/admin/reset-attendance/
```

**Headers:**
```
Authorization: Bearer TU_TOKEN_AQUI
Content-Type: application/json
```

**Body:**
```json
{
  "period_id": 5,
  "employee_ids": [10, 15, 20],
  "delete_salary_records": true,
  "dry_run": true
}
```

**Respuesta esperada:**
```json
{
  "message": "Dry run completado - No se hicieron cambios",
  "dry_run": true,
  "summary": {
    "employees_processed": 3,
    "attendance_reset": 42,
    "details_deleted": 42,
    "salary_records_deleted": 3
  },
  "employees": [
    {
      "employee_id": 10,
      "employee_username": "juan.perez",
      "attendance_to_reset": 14,
      "details_to_delete": 14,
      "current_salary_info": {
        "salary_to_pay": "1120.00",
        "total_hours": "112.00"
      }
    }
    // ... más empleados
  ]
}
```

---

### Paso 3: Ejecuta la Corrección Real

Si el dry-run se ve bien, ejecuta de nuevo **cambiando `dry_run` a `false`**:

```json
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

### Paso 4: Recalcula los Salarios Correctamente

Ahora usa tu API normal para recalcular:

**Para un empleado:**
```bash
POST https://tu-app.railway.app/payrolls/calculate/
{
  "employee_id": 10,
  "period_id": 5,
  "apply_night_factor": true
}
```

**Para todos a la vez:**
```bash
GET https://tu-app.railway.app/payrolls/calculate-all/?period_id=5&apply_night_factor=true
```

---

## 🔒 Seguridad

- ✅ Solo usuarios **staff** o **superuser** pueden usar este endpoint
- ✅ Requiere autenticación (token JWT/Bearer)
- ✅ El endpoint es temporal - puedes eliminarlo después

---

## 📋 Ejemplo Completo con Postman

**1. Abre Postman**

**2. Crea un nuevo Request:**
   - Método: `POST`
   - URL: `https://tu-app.railway.app/payrolls/admin/reset-attendance/`

**3. En la pestaña "Headers":**
   - Key: `Authorization`, Value: `Bearer tu_token_aqui`
   - Key: `Content-Type`, Value: `application/json`

**4. En la pestaña "Body" → selecciona "raw" → "JSON":**
```json
{
  "period_id": 5,
  "employee_ids": [10, 15, 20],
  "delete_salary_records": true,
  "dry_run": true
}
```

**5. Click en "Send"**

**6. Revisa la respuesta**

**7. Si todo bien, cambia `"dry_run": false` y envía de nuevo**

---

## ❓ Opciones Adicionales

### Para Resetear TODOS los empleados del período:

```json
{
  "period_id": 5,
  "employee_ids": "all",
  "delete_salary_records": true,
  "dry_run": false
}
```

### Para Solo Resetear Asistencias (NO eliminar registros de salario):

```json
{
  "period_id": 5,
  "employee_ids": [10, 15, 20],
  "delete_salary_records": false,
  "dry_run": false
}
```

⚠️ **NOTA:** No se recomienda porque el registro de salario se reemplazará con solo las nuevas horas.

---

## 🆘 Si Algo Sale Mal

### Error 403 Forbidden
- Tu usuario no es staff/superuser
- Solución: Usa un usuario administrador

### Error 404 Not Found (período)
- El `period_id` no existe
- Solución: Verifica el ID en el admin

### Error 404 Not Found (empleados)
- Los `employee_ids` no existen
- Solución: Verifica los IDs en el admin

---

## 🎯 Checklist Final

- [ ] Obtuve el ID del período (15/11-30/11)
- [ ] Obtuve los IDs de los 3 empleados
- [ ] Ejecuté dry-run y revisé la respuesta
- [ ] Ejecuté la corrección real (dry_run=false)
- [ ] Recalculé los salarios correctamente
- [ ] Verifiqué que las horas sean correctas ahora

---

**Fecha:** 29 de noviembre de 2024
**Versión:** 1.0
