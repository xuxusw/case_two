from background_task import background
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging
from .models import UserSubscription, Transaction
from users.models import User, Notification
from .payment_gateway import FakePaymentGateway

logger = logging.getLogger(__name__)

@background(schedule=60 * 5)
def check_subscription_renewals():
    """Проверяет и продлевает подписки"""
    logger.info("Запуск автоматической проверки продления подписок...")
    
    # Ищем подписки, которые скоро закончатся (за 24 часа) 
    # ИЛИ уже находятся в статусе ожидания денег
    renewal_window = timezone.now() + timedelta(hours=24)
    
    subscriptions = UserSubscription.objects.filter(
        status__in=['active', 'pending_renewal'],
        auto_renew=True,
        end_date__lte=renewal_window
    ).select_related('user', 'plan')
    
    for sub in subscriptions:
        try:
            with transaction.atomic():
                # Блокируем запись пользователя для безопасности баланса
                user = User.objects.select_for_update().get(id=sub.user.id)
                plan = sub.plan

                if user.balance < plan.price:
                    if sub.status != 'pending_renewal':
                        sub.status = 'pending_renewal'
                        sub.save()
                        Notification.objects.create(
                            user=user,
                            notification_type='payment_failed',
                            title='Недостаточно средств',
                            message=f'Для продления "{plan.name}" нужно {plan.price} руб. Пополните баланс.'
                        )
                    continue

                # Имитация платежа
                payment_result = FakePaymentGateway.process_payment(float(plan.price), user.id)
                
                if payment_result['success']:
                    user.balance -= plan.price
                    user.save()
                    
                    # Продлеваем от даты окончания или от текущей (если уже просрочена)
                    base_date = max(sub.end_date, timezone.now())
                    sub.end_date = base_date + timedelta(days=plan.duration_days)
                    sub.status = 'active'
                    sub.save()

                    Transaction.objects.create(
                        user=user,
                        subscription=sub,
                        amount=plan.price,
                        transaction_type='subscription_renewal',
                        status='completed',
                        description=f'Автопродление: {plan.name}'
                    )

                    Notification.objects.create(
                        user=user,
                        notification_type='payment_success',
                        title='Подписка продлена',
                        message=f'Подписка "{plan.name}" успешно продлена до {sub.end_date.strftime("%d.%m.%Y")}.'
                    )
        except Exception as e:
            logger.error(f"Ошибка в задаче продления для ID {sub.id}: {e}")

@background(schedule=60 * 60)
def close_expired_subscriptions():
    """Закрывает те, что так и не были оплачены и срок вышел"""
    expired = UserSubscription.objects.filter(
        status__in=['active', 'pending_renewal'],
        end_date__lt=timezone.now()
    )
    for sub in expired:
        sub.status = 'expired'
        sub.save()