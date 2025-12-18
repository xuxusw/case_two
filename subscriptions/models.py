from django.db import models

# Create your models here.

from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator  # Изменено здесь
import uuid

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    duration_days = models.IntegerField(help_text="Длительность подписки в днях")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} - {self.price} руб./{self.duration_days} дн."

class UserSubscription(models.Model):
    STATUS_CHOICES = (
        ('active', 'Активная'),
        ('pending', 'Ожидает оплаты'),
        ('expired', 'Истекла'),
        ('canceled', 'Отменена'),
        ('pending_renewal', 'Ожидает продления'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    def is_active(self):
        if self.status != 'active':
            return False
        if self.end_date and timezone.now() > self.end_date:
            self.status = 'expired'
            self.save()
            return False
        return True
    
    def days_remaining(self):
        if not self.end_date or not self.is_active():
            return 0
        delta = self.end_date - timezone.now()
        return max(0, delta.days)

class Transaction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидает'),
        ('completed', 'Завершена'),
        ('failed', 'Неуспешна'),
        ('refunded', 'Возвращена'),
    )
    
    TYPE_CHOICES = (
        ('subscription_purchase', 'Покупка подписки'),
        ('subscription_renewal', 'Продление подписки'),
        ('refund', 'Возврат'),
        ('topup', 'Пополнение баланса'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    payment_data = models.JSONField(default=dict, blank=True, help_text="Данные от платежной системы")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} руб. ({self.status})"

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_percent = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)]) 
    max_uses = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_valid(self):
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_to and 
                self.used_count < self.max_uses)
    
    def __str__(self):
        return f"{self.code} (-{self.discount_percent}%)"