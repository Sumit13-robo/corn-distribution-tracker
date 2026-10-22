from __future__ import annotations

from django.apps import AppConfig


class CornConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "corn"
    verbose_name = "Corn Distribution Tracker"

    def ready(self) -> None:
        # Import checks and fail-fast production validation at startup.
        from config.settings import validate_security

        validate_security()
