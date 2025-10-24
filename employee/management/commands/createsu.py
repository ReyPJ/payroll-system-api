from django.core.management.base import BaseCommand
from employee.models import Employee
import os


class Command(BaseCommand):
    help = 'Create a superuser from environment variables'

    def handle(self, *args, **options):
        # Get credentials from environment
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

        if not password:
            self.stdout.write(
                self.style.WARNING('DJANGO_SUPERUSER_PASSWORD not set. Skipping superuser creation.')
            )
            return

        # Check if superuser already exists
        if Employee.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser "{username}" already exists. Skipping.')
            )
            return

        # Create superuser
        try:
            Employee.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                salary_hour=0.00,  # Default value
                is_admin=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )
