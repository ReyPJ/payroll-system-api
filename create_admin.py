from employee.models import Employee

# Crear un usuario admin con valores apropiados
admin = Employee.objects.create_superuser(
    username="admin",
    email="admin@example.com",
    first_name="Reyner",
    last_name="Paniagua",
    is_admin=True,
    salary_hour=25.0,
    biweekly_hours=96.0,
    night_shift_factor=1.0,
    use_finger_print=True,
    fingerprint_hash="admin-fingerprint-verification",
)

print(
    f"Usuario admin creado con éxito: {admin.username}, is_admin={admin.is_admin}, is_superuser={admin.is_superuser}"
)
