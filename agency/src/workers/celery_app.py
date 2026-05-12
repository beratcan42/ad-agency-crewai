"""Celery uygulaması — 4 queue (q_heavy, q_fast, q_io, q_research).

Aşama 2'de sadece q_heavy aktif kullanılıyor (Account Manager için).
Aşama 3'te diğer ajanlar uygun queue'lara yönlendirilecek.
"""

from __future__ import annotations

from celery import Celery
from kombu import Queue

from ..config.settings import settings

celery_app = Celery(
    "ad_agency",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
    include=[
        "src.workers.account_manager_worker",  # geriye donuk, deprecate planlanyor
        "src.workers.agent_tasks",             # Asama 3: 12 ajan factory
    ],
)

# Queue tanımları (görev tipine göre)
celery_app.conf.task_queues = (
    Queue("q_heavy",    routing_key="heavy.#"),     # Account Manager, Strateji, Copywriter, Kreatif
    Queue("q_fast",     routing_key="fast.#"),      # Müşteri Hizmetleri, Yayın, CRM
    Queue("q_io",       routing_key="io.#"),        # Sosyal Medya, Veri Analist
    Queue("q_research", routing_key="research.#"),  # SEO, Bütçe, E-ticaret
)

celery_app.conf.update(
    task_default_queue="q_heavy",
    task_default_exchange="ad_agency",
    task_default_routing_key="heavy.default",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TZ,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True,
)

from .agent_tasks import get_task_routes  # noqa: E402

celery_app.conf.task_routes = {
    "src.workers.account_manager_worker.run": {"queue": "q_heavy", "routing_key": "heavy.account_manager"},
    **get_task_routes(),
}
