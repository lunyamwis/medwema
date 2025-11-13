from django.apps import AppConfig


class EmrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emr'

    def ready(self):
        import emr.signals