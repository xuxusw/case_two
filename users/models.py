from django.db import models

# Create your models here.

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'Пользователь'),
        ('admin', 'Администратор'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    phone = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return self.username
    
class Notification(models.Model):
    TYPE_CHOICES = (
        ('payment_success', 'Успешный платеж'),
        ('payment_failed', 'Ошибка платежа'),
        ('subscription_expiring', 'Истечение подписки'),
        ('subscription_canceled', 'Отмена подписки'),
        ('refund_processed', 'Возврат средств'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"