from django.apps import AppConfig


class PrescriptionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prescription'
    def ready(self):
        import prescription.signals