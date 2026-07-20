"""
Single place that opens the MongoDB connection used by every MongoEngine
Document in the project (patients, vitals, doctors, appointments,
notifications). Called once from core.apps.CoreConfig.ready().
"""
from mongoengine import connect, disconnect
from django.conf import settings


def connect_mongo():
    disconnect(alias="default")
    kwargs = dict(
        db=settings.MONGO_DB_NAME,
        host=settings.MONGO_HOST,
        port=settings.MONGO_PORT,
        alias="default",
    )
    if settings.MONGO_USERNAME:
        kwargs["username"] = settings.MONGO_USERNAME
        kwargs["password"] = settings.MONGO_PASSWORD
        kwargs["authentication_source"] = "admin"
    connect(**kwargs)
