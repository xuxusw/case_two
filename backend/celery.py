import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-subscription-renewals': {
        'task': 'subscriptions.tasks.check_subscription_renewals',
        'schedule': crontab(hour=0, minute=0),  # ежедневно в полночь
    },
    'send-renewal-notifications': {
        'task': 'subscriptions.tasks.send_renewal_notifications',
        'schedule': crontab(hour=9, minute=0),  # ежедневно в 9:00
    },
}