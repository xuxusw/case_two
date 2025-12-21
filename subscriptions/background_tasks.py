from background_task import background
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging
from .models import UserSubscription, Transaction, Notification
from .payment_gateway import FakePaymentGateway
from users.models import User

logger = logging.getLogger(__name__)


@background(schedule=60 * 5)  # Каждые 5 минут 
def check_subscription_renewals():
    """Проверяет и продлевает подписки (используется django-background-tasks)"""
    logger.info("Запуск автоматической проверки продления подписок...")
    
    # Находим подписки, которые заканчиваются в течение 24 часов
    renewal_date = timezone.now() + timedelta(hours=24)
    
    subscriptions = UserSubscription.objects.filter(
        status='active',
        auto_renew=True,
        end_date__lte=renewal_date,
        end_date__gt=timezone.now()  # Еще не истекли
    ).select_related('user', 'plan')
    
    renewed_count = 0
    failed_count = 0
    
    for subscription in subscriptions:
        try:
            with transaction.atomic():
                # проверка баланса
                if subscription.user.balance < subscription.plan.price:
                    # Недостаточно средств - создаем уведомление
                    Notification.objects.create(
                        user=subscription.user,
                        notification_type='payment_failed',
                        title='Недостаточно средств для автопродления',
                        message=f'Не удалось автоматически продлить подписку "{subscription.plan.name}". '
                                f'Недостаточно средств на балансе. '
                                f'Требуется: {subscription.plan.price} руб., '
                                f'доступно: {subscription.user.balance} руб.',
                        data={
                            'subscription_id': subscription.id,
                            'plan_name': subscription.plan.name,
                            'required_amount': float(subscription.plan.price),
                            'available_balance': float(subscription.user.balance)
                        }
                    )
                    
                    # Меняем статус подписки
                    subscription.status = 'pending_renewal'
                    subscription.save()
                    
                    # Создаем транзакцию с ошибкой
                    Transaction.objects.create(
                        user=subscription.user,
                        subscription=subscription,
                        amount=subscription.plan.price,
                        transaction_type='subscription_renewal',
                        status='failed',
                        description=f'Недостаточно средств для автопродления. '
                                  f'Требуется: {subscription.plan.price} руб., '
                                  f'доступно: {subscription.user.balance} руб.',
                        payment_data={'error': 'insufficient_funds'}
                    )
                    
                    logger.warning(f"Недостаточно средств для продления подписки {subscription.id}")
                    failed_count += 1
                    continue
                
                # Пытаемся списать средства
                payment_result = FakePaymentGateway.process_payment(
                    amount=float(subscription.plan.price),
                    user_id=subscription.user.id,
                    description=f"Автопродление подписки: {subscription.plan.name}"
                )
                
                if payment_result['success']:
                    # Списание средств с баланса 
                    subscription.user.balance -= subscription.plan.price
                    subscription.user.save()
                    
                    # Продлеваем подписку
                    new_end_date = subscription.end_date + timedelta(days=subscription.plan.duration_days)
                    subscription.end_date = new_end_date
                    subscription.save()
                    
                    # Создаем транзакцию
                    Transaction.objects.create(
                        user=subscription.user,
                        subscription=subscription,
                        amount=subscription.plan.price,
                        transaction_type='subscription_auto_renewal',  # Отдельный тип для автопродления
                        status='completed',
                        description=f'Автоматическое продление подписки {subscription.plan.name}',
                        payment_data=payment_result
                    )
                    
                    # СОЗДАЕМ УВЕДОМЛЕНИЕ 
                    Notification.objects.create(
                        user=subscription.user,
                        notification_type='payment_success',
                        title='Подписка автоматически продлена',
                        message=f'Ваша подписка "{subscription.plan.name}" автоматически продлена до '
                                f'{new_end_date.strftime("%d.%m.%Y")}. '
                                f'Списано {subscription.plan.price} руб. '
                                f'Новый баланс: {subscription.user.balance} руб.',
                        data={
                            'subscription_id': subscription.id,
                            'plan_name': subscription.plan.name,
                            'new_end_date': new_end_date.isoformat(),
                            'amount': str(subscription.plan.price),
                            'new_balance': float(subscription.user.balance)
                        }
                    )
                    
                    # Логируем email
                    logger.info(f"EMAIL: Автопродление для {subscription.user.email}")
                    logger.info(f"EMAIL: Подписка {subscription.plan.name} продлена до {new_end_date}")
                    
                    renewed_count += 1
                    logger.info(f"Подписка {subscription.id} успешно продлена. Новый баланс: {subscription.user.balance}")
                    
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
                    
                    # СОЗДАЕМ УВЕДОМЛЕНИЕ ОБ ОШИБКЕ
                    Notification.objects.create(
                        user=subscription.user,
                        notification_type='payment_failed',
                        title='Ошибка автопродления',
                        message=f'Не удалось автоматически продлить подписку "{subscription.plan.name}". '
                                f'Ошибка платежной системы: {payment_result["message"]}',
                        data={
                            'subscription_id': subscription.id,
                            'plan_name': subscription.plan.name,
                            'error': payment_result["message"],
                            'amount': str(subscription.plan.price)
                        }
                    )
                    
                    failed_count += 1
                    logger.warning(f"Ошибка продления подписки {subscription.id}: {payment_result['message']}")
                    
        except Exception as e:
            logger.error(f"Ошибка при обработке подписки {subscription.id}: {e}", exc_info=True)
            failed_count += 1
    
    logger.info(f"Автопроверка завершена. "
                f"Обработано: {len(subscriptions)}, "
                f"продлено: {renewed_count}, "
                f"ошибок: {failed_count}")
    
    return {
        'total_checked': len(subscriptions),
        'renewed': renewed_count,
        'failed': failed_count
    }


@background(schedule=60 * 60 * 24)  # Каждые 24 часа
def send_expiration_notifications():
    """Отправка уведомлений об истечении подписки"""
    from .models import UserSubscription
    
    # Подписки, которые истекают через 3 дня
    notification_date = timezone.now() + timedelta(days=3)
    
    subscriptions = UserSubscription.objects.filter(
        status='active',
        end_date__lte=notification_date,
        end_date__gt=timezone.now()
    ).select_related('user', 'plan')
    
    for subscription in subscriptions:
        days_left = (subscription.end_date - timezone.now()).days
        
        # Создаем уведомление
        Notification.objects.create(
            user=subscription.user,
            notification_type='subscription_expiring',
            title='Подписка скоро истечет',
            message=f'Ваша подписка "{subscription.plan.name}" истекает через {days_left} дней '
                    f'({subscription.end_date.strftime("%d.%m.%Y")}). '
                    f'Убедитесь, что на балансе достаточно средств для автопродления.',
            data={
                'subscription_id': subscription.id,
                'plan_name': subscription.plan.name,
                'days_left': days_left,
                'end_date': subscription.end_date.isoformat(),
                'plan_price': float(subscription.plan.price)
            }
        )
        
        # Логируем email
        logger.info(f"EMAIL: Уведомление об истечении для {subscription.user.email}")
        logger.info(f"EMAIL: Подписка {subscription.plan.name} истекает через {days_left} дней")
    
    return {'notifications_sent': len(subscriptions)}


@background(schedule=60 * 60)  # Каждый час
def retry_failed_payments():
    """Повторная попытка оплаты для подписок в статусе pending_renewal"""
    subscriptions = UserSubscription.objects.filter(
        status='pending_renewal',
        auto_renew=True
    ).select_related('user', 'plan')
    
    retried_count = 0
    success_count = 0
    
    for subscription in subscriptions:
        try:
            # Проверяем, может баланс пополнился
            if subscription.user.balance >= subscription.plan.price:
                payment_result = FakePaymentGateway.process_payment(
                    amount=float(subscription.plan.price),
                    user_id=subscription.user.id,
                    description=f"Повторная попытка оплаты: {subscription.plan.name}"
                )
                
                if payment_result['success']:
                    # Списание средств
                    subscription.user.balance -= subscription.plan.price
                    subscription.user.save()
                    
                    # Продлеваем подписку
                    new_end_date = timezone.now() + timedelta(days=subscription.plan.duration_days)
                    subscription.end_date = new_end_date
                    subscription.status = 'active'
                    subscription.save()
                    
                    # Создаем транзакцию
                    Transaction.objects.create(
                        user=subscription.user,
                        subscription=subscription,
                        amount=subscription.plan.price,
                        transaction_type='subscription_renewal',
                        status='completed',
                        description='Повторная успешная оплата',
                        payment_data=payment_result
                    )
                    
                    # Уведомление
                    Notification.objects.create(
                        user=subscription.user,
                        notification_type='payment_success',
                        title='Платеж успешно выполнен',
                        message=f'Повторная попытка оплаты подписки "{subscription.plan.name}" успешна. '
                                f'Подписка продлена до {new_end_date.strftime("%d.%m.%Y")}.',
                        data={
                            'subscription_id': subscription.id,
                            'plan_name': subscription.plan.name,
                            'new_end_date': new_end_date.isoformat()
                        }
                    )
                    
                    success_count += 1
                    
            retried_count += 1
            
        except Exception as e:
            logger.error(f"Ошибка при повторной попытке оплаты {subscription.id}: {e}")
    
    return {
        'retried': retried_count,
        'success': success_count
    }