# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django REST Framework API for a payroll management system. Handles employee attendance tracking via NFC, biweekly pay period calculations, and automated salary computations with support for regular hours, night shift differentials, overtime, and lunch deductions.

## Key Development Commands

### Database & Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Run Development Server
```bash
python manage.py runserver
```

### Create Admin User
```bash
python manage.py createsu
```
Uses environment variables `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PIN` to create admin with PIN authentication.

### Generate Test Data
```bash
python create_test_data.py
```
Creates sample employees, pay periods, attendance records, and timers.

### Custom Management Commands
```bash
# Reset attendance paid status (Railway-compatible)
python manage.py reset_attendance_paid_status
```

### Production Deployment (Railway)
Procfile command:
```bash
python manage.py migrate && python manage.py collectstatic --noinput && python manage.py createsu && gunicorn core.wsgi --log-file -
```

## Architecture

### Core Apps Structure

- **employee**: Custom user model (Employee) extending AbstractUser
  - Fields: phone, salary_hour, biweekly_hours, night_shift_factor, is_admin, unique_pin
  - Authentication uses PIN instead of password via unique_pin field

- **authentication**: JWT-based auth system
  - Uses djangorestframework_simplejwt
  - Token lifetime: 24 hours (configured in settings.SIMPLE_JWT)

- **attendance**: Time tracking system
  - AttendanceRegister: Clock in/out records via NFC
  - AttendanceDetail: Daily breakdown of hours (regular, night, extra, lunch deduction)
  - Unique constraint on (employee, work_date) in AttendanceDetail

- **timers**: Expected work schedules
  - Timer model: day of week (0-6), timeIn, timeOut, is_active, is_night_shift
  - Unique constraint on (employee, day)

- **payrolls**: Salary calculation engine
  - PayPeriod: Biweekly periods with start_date, end_date, is_closed
  - SalaryRecord: Computed salaries with hours breakdown
  - Key service: `payrolls/services/calculate_payroll.py`

- **core**: Project configuration
  - Settings, URLs, permissions (IsAdmin custom permission)
  - Timezone: America/Costa_Rica
  - Custom user model: employee.Employee

### URL Structure (API v1)

All endpoints under `/v1/` prefix:
- `/v1/employee/` - Employee management
- `/v1/auth/` - Authentication (login, token refresh)
- `/v1/attendance/` - Attendance registers
- `/v1/timer/` - Work schedules
- `/v1/salary/` - Payroll calculations and records
- `/v1/docs/` - OpenAPI schema (drf-spectacular)
- `/v1/docs/swagger/` - Swagger UI
- `/v1/docs/redoc/` - ReDoc UI

### Key Business Logic

**Night Shift Calculation** (`payrolls/services/calculate_payroll.py:calculate_night_hours`):
- Night hours: 7:00 PM (19:00) to 6:00 AM (06:00)
- Calculates actual night hours worked during a shift
- Night pay = night_hours × salary_hour × (night_shift_factor - 1.0)

**Salary Calculation** (`SalaryRecord.calculate_salary`):
- Regular hours: Up to biweekly_hours limit (default 96.0)
- Overtime: Hours beyond biweekly_hours × 1.5 rate
- Night differential: Applied to night_hours if apply_night_factor=True
- Deductions: lunch_deduction_hours and other_deductions
- Formula: gross_salary = (regular_pay + night_pay + extra_pay)
- Final: salary_to_pay = gross_salary - lunch_deduction - other_deductions

**Pay Period Protection**:
Recent fix prevents calculating salaries before pay period ends. Check git history for details on "protección contra cálculo temprano" (early calculation protection).

**Period Closure & Migration** (`payrolls/services/period_migration.py`):
- System operates 24/7, so there are always employees working when closing periods
- When closing a period: automatically migrates current shifts to new period
- Migration criteria: timestamp_in from TODAY, timestamp_out=NULL, paid=False
- Prevents hours from being "trapped" in closed periods
- Uses atomic transactions to ensure data consistency
- Endpoint: POST /v1/salary/period/ with action="close_and_create_new"

### Database

PostgreSQL database configured via `dj_database_url`:
- Production: Uses Railway's DATABASE_URL
- Local dev: Individual DB_* environment variables or DATABASE_URL

### Permissions System

- IsAuthenticated: Standard DRF permission
- IsAdmin: Custom permission (core/permissions.py) checks request.user.is_admin
- Admin views in payrolls/views_admin.py use IsAdmin permission

### Environment Variables

See `.env.example` for required variables:
- SECRET_KEY, DEBUG, ALLOWED_HOSTS, ENVIRONMENT
- DATABASE_URL or DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT
- FRONTEND_URL (for CORS)
- DJANGO_SUPERUSER_USERNAME/EMAIL/PIN (for createsu command)

### CORS Configuration

Configured for frontend integration:
- CORS_ALLOWED_ORIGINS includes FRONTEND_URL and localhost:3000
- CORS_ALLOW_CREDENTIALS = True
- CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

### Deployment Notes

- Deployed on Railway
- Celery/Redis features commented out in settings (not used for Railway deployment)
- Twilio WhatsApp integration commented out
- Static files collected to BASE_DIR/staticfiles
- Security settings conditional on ENVIRONMENT=production

### Testing

Test files exist in each app but are mostly empty boilerplate. No comprehensive test suite currently implemented.
