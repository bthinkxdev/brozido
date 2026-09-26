"""ASGI config for brozido."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brozido.settings.prod")

application = get_asgi_application()
