import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'furja.settings')

app = Celery('furja')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.task_acks_late = True
app.conf.worker_concurrency = 5
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_max_tasks_per_child = 2
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

app.conf.beat_schedule = {
    'cleanup_old_tasks': {
        'task': 'ytdown.tasks.cleanup_old_tasks',
        'schedule': crontab(minute=0, hour=0),
    },
    'update_yt_dlp': {
        'task': 'ytdown.tasks.update_yt_dlp',
        'schedule': crontab(hour=0, minute=0),
    },
}

app.autodiscover_tasks()
