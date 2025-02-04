import os
from celery import Celery

# Establecer el entorno de configuración de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")

# Cargar la configuración de Celery desde settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-descubrir tareas en todas las apps registradas en Django
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
