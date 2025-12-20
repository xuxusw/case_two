from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import UserSubscription, Transaction
from .payment_gateway import FakePaymentGateway
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_subscription_renewals():
    """Проверяет и продлевает подписки"""
    from django.db import transaction as db_transaction
    
    # Находим подписки, которые заканчиваются в течение 1 дня
    renewal_date = timezone.now() + timedelta(days=1)
    
    subscriptions = UserSubscription.objects.filter(
        status='active',
        auto_renew=True,
        end_date__lte=renewal_date,
        end_date__gt=timezone.now()  # Еще не истекли
    ).select_related('user', 'plan').select_for_update()
    
    renewed_count = 0
    failed_count = 0
    
    for subscription in subscriptions:
        with db_transaction.atomic():
            try:
                # Пытаемся списать средства
                payment_result = FakePaymentGateway.process_payment(
                    amount=float(subscription.plan.price),
                    user_id=subscription.user.id,
                    description=f"Автопродление подписки: {subscription.plan.name}"
                )
                
                if payment_result['success']:
                    # Продлеваем подписку
                    new_end_date = subscription.end_date + timedelta(days=subscription.plan.duration_days)
                    subscription.end_date = new_end_date
                    subscription.save()
                    
                    # Создаем транзакцию
                    Transaction.objects.create(
                        user=subscription.user,
                        subscription=subscription,
                        amount=subscription.plan.price,
                        transaction_type='subscription_renewal',
                        status='completed',
                        description=f'Автопродление подписки {subscription.plan.name}',
                        payment_data=payment_result
                    )
                    
                    renewed_count += 1
                    logger.info(f"Подписка {subscription.id} успешно продлена")
                else:
                    # Платеж не прошел
                    subscription.status = 'pending_renewal'
                    subscription.save()
                    
                    Transaction.objects.create(
                        user=subscription.user,
                        subscription=subscription,
                        amount=subscription.plan.price,
                        transaction_type='subscription_renewal',
                        status='failed',
                        description=f'Ошибка автопродления: {payment_result["message"]}',
                        payment_data=payment_result
                    )
                    
                    failed_count += 1
                    logger.warning(f"Ошибка продления подписки {subscription.id}: {payment_result['message']}")
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке подписки {subscription.id}: {e}")
                failed_count += 1
    
    return {
        'renewed': renewed_count,
        'failed': failed_count,
        'total': len(subscriptions)
    }

@shared_task
def send_renewal_notifications():
    
    from .models import UserSubscription
    from datetime import timedelta
    
    # Подписки, которые истекают через 3 дня
    notification_date = timezone.now() + timedelta(days=3)
    
    subscriptions = UserSubscription.objects.filter(
        status='active',
        end_date__lte=notification_date,
        end_date__gt=timezone.now()
    )
    
    for subscription in subscriptions:
        # сюда надо логику отправки email
        days_left = (subscription.end_date - timezone.now()).days
        logger.info(f"Уведомление: Подписка {subscription.id} истекает через {days_left} дней")
    
    return {'notifications_sent': len(subscriptions)}