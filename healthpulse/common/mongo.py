"""
Single place that opens the MongoDB connection used by every MongoEngine
Document in the project (patients, vitals, doctors, appointments,
notifications). Called once from core.apps.CoreConfig.ready().
"""
import logging
from mongoengine import connect, disconnect
from django.conf import settings

logger = logging.getLogger(__name__)


def connect_mongo():
    disconnect(alias="default")
    kwargs = dict(
        db=settings.MONGO_DB_NAME,
        host=settings.MONGO_HOST,
        port=settings.MONGO_PORT,
        alias="default",
        serverSelectionTimeoutMS=2000,
    )
    if settings.MONGO_USERNAME:
        kwargs["username"] = settings.MONGO_USERNAME
        kwargs["password"] = settings.MONGO_PASSWORD
        kwargs["authentication_source"] = "admin"

    try:
        conn = connect(**kwargs)
        # Test if server is responsive
        conn.admin.command("ping")
        logger.info("Connected to MongoDB at %s:%s", settings.MONGO_HOST, settings.MONGO_PORT)
    except Exception as exc:
        logger.warning(
            "Could not connect to MongoDB at %s:%s (%s). Falling back to in-memory mongomock database.",
            settings.MONGO_HOST,
            settings.MONGO_PORT,
            exc,
        )
        try:
            disconnect(alias="default")
        except Exception:
            pass

        try:
            import mongomock
            connect(
                db=settings.MONGO_DB_NAME,
                host=settings.MONGO_HOST,
                mongo_client_class=mongomock.MongoClient,
                alias="default",
            )
            logger.info("Successfully connected to in-memory mongomock database.")
        except Exception as mock_exc:
            logger.warning("Failed to initialize mongomock fallback: %s", mock_exc)

