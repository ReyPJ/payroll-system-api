from django.core.management.base import BaseCommand
from employee.models import Employee
import os


class Command(BaseCommand):
    help = 'Create a superuser from environment variables (using PIN authentication)'

    def handle(self, *args, **options):
        # Get credentials from environment
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        unique_pin = os.getenv('DJANGO_SUPERUSER_PIN')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'temp_password_123')  # Temporary, won't be used

        if not unique_pin:
            self.stdout.write(
                self.style.WARNING('DJANGO_SUPERUSER_PIN not set. Skipping superuser creation.')
            )
            return

        # Check if superuser already exists by username or PIN
        if Employee.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser with username "{username}" already exists. Skipping.')
            )
            return

        if Employee.objects.filter(unique_pin=unique_pin).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser with PIN "{unique_pin}" already exists. Skipping.')
            )
            return

        # Create superuser with PIN authentication
        try:
            superuser = Employee.objects.create_superuser(
                username=username,
                email=email,
                password=password,  # Required by Django but not used for login
                salary_hour=0.00,  # Default value
                is_admin=True
            )
            # Set the unique PIN for authentication
            superuser.unique_pin = unique_pin
            superuser.save()

            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully with PIN!')
            )
            self.stdout.write(
                self.style.SUCCESS(f'You can now login using PIN: {unique_pin}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )
