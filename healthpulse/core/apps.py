from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from common.mongo import connect_mongo
        from common.sync import sync_all_profiles_to_mongo
        connect_mongo()
        sync_all_profiles_to_mongo()
