import sys
import os
from django.apps import AppConfig

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        # Run only in real server process (not reloader)
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") == "true":
            from .pipline import run_pipeline
            run_pipeline()
            from .cron import start_scheduler
            start_scheduler()