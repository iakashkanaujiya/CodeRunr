from celery import Celery
from celery.signals import setup_logging, worker_process_init

from config import settings, configure_logger

app = Celery(
    "worker",
    include=["worker.tasks"],
    backend=settings.REDIS_URL,
    broker=settings.REDIS_URL,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 3600,
        "retry_policy": {"timeout": 5.0},
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,
    timezone="Asia/Kolkata",
    enable_utc=True,
)

app.conf.update(
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
)


@setup_logging.connect
def setup_celery_logging(**_: object) -> None:
    configure_logger()


@worker_process_init.connect
def setup_worker_logging(**_: object) -> None:
    configure_logger()


if __name__ == "__main__":
    app.start()
