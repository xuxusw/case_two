from django.core.management.base import BaseCommand
from subscriptions.background_tasks import (
    check_subscription_renewals,
    send_expiration_notifications,
    retry_failed_payments
)
from background_task.models import Task
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Запускает все фоновые задачи для системы подписок'
    
    def handle(self, *args, **options):
        self.stdout.write("=== ЗАПУСК ФОНОВЫХ ЗАДАЧ СИСТЕМЫ ПОДПИСОК ===")
        
        # Удаляем старые задачи 
        Task.objects.all().delete()
        self.stdout.write("Старые задачи удалены")
        
        # Запускаем задачи
        check_subscription_renewals(repeat=300, repeat_until=None)  # Каждые 5 минут
        self.stdout.write(self.style.SUCCESS("Задача проверки продления запущена (каждые 5 мин)"))
        
        send_expiration_notifications(repeat=86400, repeat_until=None)  # Каждые 24 часа
        self.stdout.write(self.style.SUCCESS("Задача отправки уведомлений запущена (каждые 24 часа)"))
        
        retry_failed_payments(repeat=3600, repeat_until=None)  # Каждый час
        self.stdout.write(self.style.SUCCESS("Задача повторных попыток платежей запущена (каждый час)"))
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("ВСЕ ФОНОВЫЕ ЗАДАЧИ ЗАПУЩЕНЫ."))
        self.stdout.write("\nТеперь запустите в ОТДЕЛЬНОМ терминале:")
        self.stdout.write(self.style.WARNING("python manage.py process_tasks"))
        self.stdout.write("\nИ оставьте его работать в фоне.")
        self.stdout.write("="*60)