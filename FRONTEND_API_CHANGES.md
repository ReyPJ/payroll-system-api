# 📱 Cambios en la API - Documentación para Frontend

## 🆕 Nuevos Endpoints y Cambios Importantes

### 1. **Warnings en Cálculo de Salarios** ⚠️

Los endpoints de cálculo de salarios ahora devuelven **advertencias** cuando detectan situaciones problemáticas.

#### Endpoints Afectados:
- `POST /payrolls/calculate/` - Calcular salario individual
- `GET /payrolls/calculate-all/` - Calcular todos los salarios

#### Cambios en la Respuesta:

**ANTES:**
```json
{
  "id": 123,
  "employee": 10,
  "total_hours": "112.00",
  "salary_to_pay": "1120.00"
}
```

**AHORA (cuando hay warnings):**
```json
{
  "salary_record": {
    "id": 123,
    "employee": 10,
    "total_hours": "112.00",
    "salary_to_pay": "1120.00"
  },
  "warnings": [
    {
      "type": "early_calculation",
      "message": "⚠️ ADVERTENCIA: Estás calculando el salario 2 día(s) antes del fin del período (30/11/2024)",
      "details": "Si el empleado sigue trabajando, tendrás que recalcular usando el comando 'reset_attendance_paid_status'",
      "days_remaining": 2,
      "period_end_date": "2024-11-30"
    },
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

#### Tipos de Warnings:

1. **`early_calculation`** - Calcular antes del fin del período
   - Campos: `days_remaining`, `period_end_date`

2. **`recalculation`** - Ya existe un cálculo previo
   - Campos: `previous_calculation_date`, `previous_total_hours`, `previous_salary`

#### Implementación en Frontend:

```typescript
interface SalaryWarning {
  type: 'early_calculation' | 'recalculation';
  message: string;
  details: string;
  days_remaining?: number;
  period_end_date?: string;
  previous_calculation_date?: string;
  previous_total_hours?: string;
  previous_salary?: string;
}

interface SalaryResponse {
  salary_record?: SalaryRecord;  // Si hay warnings, los datos van aquí
  warnings?: SalaryWarning[];
  // Si NO hay warnings, los datos vienen directamente en el root
  id?: number;
  employee?: number;
  // ...
}

// Ejemplo de uso
const response = await calculateSalary(employeeId);

if (response.warnings && response.warnings.length > 0) {
  // Mostrar advertencias al usuario
  response.warnings.forEach(warning => {
    showWarning(warning.message, warning.details);
  });

  // Los datos del salario están en salary_record
  const salaryData = response.salary_record;
} else {
  // No hay warnings, los datos vienen directamente
  const salaryData = response;
}
```

---

### 2. **Nuevo Endpoint: Resumen de Horas en Tiempo Real** 🕐

Ver las horas acumuladas **sin calcular el salario** ni marcar registros como pagados.

#### Endpoint:
```
GET /payrolls/live-summary/?period_id=5&employee_id=10
GET /payrolls/live-summary/?period_id=5  (todos los empleados)
GET /payrolls/live-summary/  (período activo, todos los empleados)
```

#### Parámetros:
- `period_id` (opcional): ID del período. Si no se proporciona, usa el activo.
- `employee_id` (opcional): ID del empleado. Si no se proporciona, devuelve todos.

#### Respuesta:
```json
{
  "period": {
    "id": 5,
    "description": "Quincena 15/11/2024 - 30/11/2024",
    "start_date": "2024-11-15",
    "end_date": "2024-11-30",
    "is_closed": false
  },
  "employees": [
    {
      "employee_id": 10,
      "employee_username": "juan.perez",
      "employee_full_name": "Juan Perez",
      "total_hours": "112.50",
      "regular_hours": "96.00",
      "night_hours": "2.50",
      "extra_hours": "16.50",
      "estimated_salary": "1250.00",
      "days_worked": 14,
      "pending_checkout": 0
    }
  ],
  "total_employees": 1
}
```

#### Casos de Uso:

1. **Dashboard en Tiempo Real**
   - Mostrar horas acumuladas durante el período activo
   - No requiere calcular salario

2. **Verificación Antes de Calcular**
   - Ver el resumen antes de ejecutar el cálculo oficial

3. **Monitoreo de Empleados**
   - Ver quién tiene registros pendientes de salida (`pending_checkout`)

#### Implementación en Frontend:

```typescript
interface LiveSummaryEmployee {
  employee_id: number;
  employee_username: string;
  employee_full_name: string;
  total_hours: string;
  regular_hours: string;
  night_hours: string;
  extra_hours: string;
  estimated_salary: string;
  days_worked: number;
  pending_checkout: number;
}

interface LiveSummaryResponse {
  period: {
    id: number;
    description: string;
    start_date: string;
    end_date: string;
    is_closed: boolean;
  };
  employees: LiveSummaryEmployee[];
  total_employees: number;
}

// Ejemplo de uso
const fetchLiveSummary = async (periodId?: number, employeeId?: number) => {
  const params = new URLSearchParams();
  if (periodId) params.append('period_id', periodId.toString());
  if (employeeId) params.append('employee_id', employeeId.toString());

  const response = await fetch(`/payrolls/live-summary/?${params}`);
  const data: LiveSummaryResponse = await response.json();

  return data;
};

// Dashboard component
const Dashboard = () => {
  const [summary, setSummary] = useState<LiveSummaryResponse | null>(null);

  useEffect(() => {
    const loadSummary = async () => {
      const data = await fetchLiveSummary();
      setSummary(data);
    };

    loadSummary();
    // Actualizar cada 30 segundos
    const interval = setInterval(loadSummary, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h2>Período: {summary?.period.description}</h2>
      {summary?.employees.map(emp => (
        <EmployeeCard key={emp.employee_id} employee={emp} />
      ))}
    </div>
  );
};
```

---

### 3. **Nuevo Endpoint: Resetear Asistencias (Admin)** 🔧

Para corregir cálculos tempranos.

#### Endpoint:
```
POST /payrolls/admin/reset-attendance/
```

#### Requiere:
- Autenticación
- Usuario staff o superuser

#### Body:
```json
{
  "period_id": 5,
  "employee_ids": [10, 15, 20],  // o "all"
  "delete_salary_records": true,
  "dry_run": false
}
```

#### Respuesta:
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
  "employees": [
    {
      "employee_id": 10,
      "employee_username": "juan.perez",
      "attendance_reset": 14,
      "details_deleted": 14,
      "salary_records_deleted": 1,
      "current_salary_info": {
        "salary_to_pay": "1120.00",
        "total_hours": "112.00",
        "calculated_at": "2024-11-28T10:30:00Z"
      }
    }
  ],
  "next_steps": [
    "Los empleados están listos para recalcular",
    "Usa POST /payrolls/calculate/ para recalcular"
  ]
}
```

#### Implementación en Frontend:

```typescript
interface ResetAttendanceRequest {
  period_id: number;
  employee_ids: number[] | 'all';
  delete_salary_records?: boolean;
  dry_run?: boolean;
}

const resetAttendance = async (request: ResetAttendanceRequest) => {
  const response = await fetch('/payrolls/admin/reset-attendance/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('No tienes permisos para esta operación');
    }
    throw new Error('Error al resetear asistencias');
  }

  return await response.json();
};

// Ejemplo con confirmación
const handleReset = async () => {
  // 1. Dry-run primero
  const dryRunResult = await resetAttendance({
    period_id: 5,
    employee_ids: [10, 15, 20],
    delete_salary_records: true,
    dry_run: true
  });

  // 2. Mostrar confirmación
  const confirmed = await confirmDialog(
    `Se resetearán ${dryRunResult.summary.attendance_reset} asistencias. ¿Continuar?`
  );

  if (confirmed) {
    // 3. Ejecutar real
    const result = await resetAttendance({
      period_id: 5,
      employee_ids: [10, 15, 20],
      delete_salary_records: true,
      dry_run: false
    });

    showSuccess(result.message);
  }
};
```

---

## 🐛 **Bug Fix: Cálculo de Horas Nocturnas**

### Problema Corregido:
Antes, si un turno tenía **cualquier** hora nocturna, **todo** el turno se marcaba como nocturno.

**Ejemplo del Bug:**
- Entrada: 8:00 AM
- Salida: 9:00 PM
- **Antes:** 13 horas nocturnas ❌
- **Ahora:** 2 horas nocturnas (7PM-9PM) ✅

### Cambios:
- Nueva función `calculate_night_hours()` que calcula **exactamente** cuántas horas cayeron en horario nocturno (7PM-6AM)
- Afecta a todos los cálculos de salario y resúmenes

### Impacto en Frontend:
**Ningún cambio** en las interfaces. Los valores simplemente serán más precisos.

---

## 📊 Resumen de Endpoints

| Endpoint | Método | Propósito | Cambios |
|----------|--------|-----------|---------|
| `/payrolls/calculate/` | POST | Calcular salario individual | ✨ Ahora devuelve warnings |
| `/payrolls/calculate-all/` | GET | Calcular todos los salarios | ✨ Ahora devuelve warnings |
| `/payrolls/live-summary/` | GET | Ver horas en tiempo real | 🆕 Nuevo endpoint |
| `/payrolls/admin/reset-attendance/` | POST | Resetear asistencias (admin) | 🆕 Nuevo endpoint |

---

## 🎨 Recomendaciones de UI/UX

### 1. Mostrar Warnings
```tsx
// Componente de Warning
const SalaryWarning = ({ warning }: { warning: SalaryWarning }) => {
  const getIcon = () => {
    switch (warning.type) {
      case 'early_calculation': return '⏰';
      case 'recalculation': return '🔄';
      default: return '⚠️';
    }
  };

  return (
    <div className="warning-card bg-yellow-100 border-l-4 border-yellow-500 p-4">
      <div className="flex items-start">
        <span className="text-2xl mr-3">{getIcon()}</span>
        <div>
          <p className="font-bold">{warning.message}</p>
          <p className="text-sm text-gray-700 mt-1">{warning.details}</p>
          {warning.days_remaining && (
            <p className="text-xs text-gray-600 mt-2">
              Faltan {warning.days_remaining} días para el fin del período
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
```

### 2. Dashboard en Tiempo Real
```tsx
const LiveDashboard = () => {
  const { data, isLoading } = useQuery(
    ['live-summary'],
    () => fetchLiveSummary(),
    { refetchInterval: 30000 } // Actualizar cada 30s
  );

  return (
    <div>
      <h2>Horas Acumuladas - {data?.period.description}</h2>
      <div className="grid grid-cols-3 gap-4">
        {data?.employees.map(emp => (
          <Card key={emp.employee_id}>
            <h3>{emp.employee_full_name}</h3>
            <div className="stats">
              <Stat label="Total Horas" value={emp.total_hours} />
              <Stat label="Horas Regulares" value={emp.regular_hours} />
              <Stat label="Horas Nocturnas" value={emp.night_hours} />
              <Stat label="Horas Extra" value={emp.extra_hours} />
              <Stat label="Salario Estimado" value={`$${emp.estimated_salary}`} />
            </div>
            {emp.pending_checkout > 0 && (
              <Badge variant="warning">
                {emp.pending_checkout} registro(s) sin salida
              </Badge>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
};
```

### 3. Confirmación para Cálculo Temprano
```tsx
const calculateWithConfirmation = async (employeeId: number) => {
  const response = await calculateSalary(employeeId);

  if (response.warnings?.some(w => w.type === 'early_calculation')) {
    const confirmed = await confirmDialog({
      title: 'Calcular Antes de Tiempo',
      message: 'Estás calculando antes del fin del período. Si el empleado sigue trabajando, tendrás que recalcular. ¿Continuar?',
      confirmText: 'Sí, calcular ahora',
      cancelText: 'Cancelar'
    });

    if (!confirmed) {
      return null;
    }
  }

  return response.salary_record || response;
};
```

---

## 🚀 Migración

### Paso 1: Actualizar Tipos TypeScript
```bash
# Regenerar tipos si usas codegen
npm run generate:types
```

### Paso 2: Actualizar Componentes
Buscar usos de `/payrolls/calculate/` y `/payrolls/calculate-all/` y agregar manejo de warnings.

### Paso 3: Implementar Live Summary
Agregar dashboard de horas en tiempo real.

### Paso 4: Agregar Endpoint de Reset (Solo Admin)
Solo si tu frontend tiene panel de administración.

---

**Fecha:** 29 de noviembre de 2024
**Versión API:** 2.0
