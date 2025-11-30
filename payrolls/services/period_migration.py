"""
Servicios para migración de registros de asistencia entre períodos de pago
"""
from django.utils import timezone
from attendance.models import AttendanceRegister
from payrolls.models import PayPeriod
from typing import List, Dict, Any


def migrate_current_shifts_to_new_period(
    closing_period: PayPeriod, new_period: PayPeriod
) -> Dict[str, Any]:
    """
    Migra las entradas actuales (sin salida) al nuevo período de pago.

    Esta función identifica los registros de asistencia que:
    - Tienen timestamp_in del día de hoy
    - NO tienen timestamp_out (aún están trabajando)
    - NO están marcados como pagados

    Y los migra al nuevo período eliminándolos del período que se está cerrando
    y recreándolos en el nuevo período con los mismos datos.

    Args:
        closing_period: El período que se está cerrando
        new_period: El nuevo período donde se migrarán las entradas actuales

    Returns:
        Dict con información sobre la migración:
        {
            "migrated_count": int,
            "migrated_records": List[Dict],
            "message": str
        }
    """
    # Obtener la fecha actual
    today = timezone.now().date()

    # Buscar SOLO las entradas de hoy sin salida y sin pagar
    # Estas son las personas que están trabajando actualmente
    current_shifts = AttendanceRegister.objects.filter(
        timestamp_in__date=today,  # Solo de HOY
        timestamp_out__isnull=True,  # Sin salida (aún trabajando)
        paid=False,  # No pagados
    )

    migrated_records = []

    # Migrar cada registro
    for shift in current_shifts:
        # Guardar información del registro original
        record_info = {
            "employee_id": shift.employee.id,
            "employee_username": shift.employee.username,
            "timestamp_in": shift.timestamp_in.isoformat(),
            "method": shift.method,
            "nfc_token": shift.nfc_token,
        }

        # Crear copia en el nuevo período
        new_shift = AttendanceRegister.objects.create(
            employee=shift.employee,
            timestamp_in=shift.timestamp_in,  # Mantener el mismo timestamp
            timestamp_out=None,  # Sin salida
            method=shift.method,
            nfc_token=shift.nfc_token,
            paid=False,
            pay_period=new_period,  # Asignar al nuevo período
            sync=False,
        )

        record_info["new_record_id"] = new_shift.id
        record_info["migrated_to_period"] = new_period.description

        # Eliminar el registro del período que se está cerrando
        shift.delete()

        migrated_records.append(record_info)

    return {
        "migrated_count": len(migrated_records),
        "migrated_records": migrated_records,
        "message": f"Se migraron {len(migrated_records)} entradas al nuevo período",
    }
