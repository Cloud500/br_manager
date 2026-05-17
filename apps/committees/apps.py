from django.apps import AppConfig
from importlib import import_module

class CommitteesConfig(AppConfig):
    name = 'apps.committees'

    def ready(self):
        import_module("apps.committees.permissions")
        import_module("apps.committees.roles")
