from django.db import models
from django.utils import timezone
from .models import UserSubscription

class FailedPayment(models.Model):
    """Очередь неудачных платежей для повторной попытки"""
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    attempt_count = models.IntegerField(default=1)
    last_attempt = models.DateTimeField(auto_now=True)
    next_attempt = models.DateTimeField()
    error_message = models.TextField()
    
    def schedule_retry(self):
        self.attempt_count += 1
        delay_hours = min(24, 2 ** self.attempt_count)  # экспоненциальная задержка
        self.next_attempt = timezone.now() + timezone.timedelta(hours=delay_hours)
        self.save()