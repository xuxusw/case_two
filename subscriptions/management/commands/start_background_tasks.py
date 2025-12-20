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
        
        # Удаляем старые задачи (опционально)
        Task.objects.all().delete()
        self.stdout.write("Старые задачи удалены")
        
        # Запускаем задачу проверки продления (каждые 60 секунд для тестирования)
        check_subscription_renewals(repeat=60) 
        self.stdout.write(self.style.SUCCESS("Задача проверки продления запущена (каждые 60 сек)"))
        
        # Запускаем задачу отправки уведомлений (каждые 5 минут)
        send_expiration_notifications(repeat=300)  
        self.stdout.write(self.style.SUCCESS("Задача отправки уведомлений запущена (каждые 5 мин)"))
        
        # Запускаем задачу повторных попыток платежей (каждые 10 минут)
        retry_failed_payments(repeat=600) 
        self.stdout.write(self.style.SUCCESS("Задача повторных попыток платежей запущена (каждые 10 мин)"))
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("ВСЕ ФОНОВЫЕ ЗАДАЧИ ЗАПУЩЕНЫ!"))
        self.stdout.write("\nТеперь запустите в ОТДЕЛЬНОМ терминале:")
        self.stdout.write(self.style.WARNING("python manage.py process_tasks"))
        self.stdout.write("\nИ оставьте его работать в фоне.")
        self.stdout.write("="*50)