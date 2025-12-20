from background_task import background
from django.utils import timezone
from datetime import timedelta
import logging
from django.db import transaction as db_transaction

from .models import UserSubscription, Transaction
from .payment_gateway import FakePaymentGateway
from users.models import Notification, User

logger = logging.getLogger(__name__)

@background(schedule=60)  # запуск каждые 60 сек (для тестирования)
def check_subscription_renewals():
    """
    Фоновая задача для автоматического продления подписок.
    """
    logger.info("=== ЗАПУСК ФОНОВОЙ ЗАДАЧИ: ПРОВЕРКА ПРОДЛЕНИЯ ПОДПИСОК ===")
    
    try:
        # Находим подписки, которые заканчиваются в течение 24 часов
        renewal_date = timezone.now() + timedelta(hours=24)
        
        subscriptions = UserSubscription.objects.filter(
            status='active',
            auto_renew=True,
            end_date__lte=renewal_date,
            end_date__gt=timezone.now()  # Еще не истекли
        ).select_related('user', 'plan')
        
        logger.info(f"Найдено подписок для проверки: {len(subscriptions)}")
        
        renewed_count = 0
        failed_count = 0
        
        for subscription in subscriptions:
            try:
                logger.info(f"Обработка подписки ID {subscription.id}, пользователь: {subscription.user.username}")
                
                # Используем транзакцию для безопасности
                with db_transaction.atomic():
                    # Блокируем подписку для обработки
                    locked_subscription = UserSubscription.objects.select_for_update().get(id=subscription.id)
                    
                    # Дополнительная проверка
                    if not (locked_subscription.auto_renew and locked_subscription.status == 'active'):
                        logger.info(f"Пропуск подписки {locked_subscription.id}: не подлежит продлению")
                        continue
                    
                    # Имитация платежа через фейковую платежную систему
                    payment_result = FakePaymentGateway.process_payment(
                        amount=float(locked_subscription.plan.price),
                        user_id=locked_subscription.user.id,
                        description=f"Автоматическое продление: {locked_subscription.plan.name}"
                    )
                    
                    if payment_result['success']:
                        # УСПЕШНЫЙ ПЛАТЕЖ
                        # Продлеваем подписку
                        new_end_date = locked_subscription.end_date + timedelta(days=locked_subscription.plan.duration_days)
                        locked_subscription.end_date = new_end_date
                        locked_subscription.save()
                        
                        # Создаем транзакцию
                        Transaction.objects.create(
                            user=locked_subscription.user,
                            subscription=locked_subscription,
                            amount=locked_subscription.plan.price,
                            transaction_type='subscription_renewal',
                            status='completed',
                            description=f'Автоматическое продление подписки {locked_subscription.plan.name}',
                            payment_data=payment_result
                        )
                        
                        # Создаем уведомление для пользователя
                        Notification.objects.create(
                            user=locked_subscription.user,
                            notification_type='payment_success',
                            title='Подписка продлена',
                            message=f'Ваша подписка "{locked_subscription.plan.name}" автоматически продлена до {new_end_date.strftime("%d.%m.%Y")}',
                            data={
                                'subscription_id': locked_subscription.id,
                                'new_end_date': new_end_date.isoformat(),
                                'amount': float(locked_subscription.plan.price)
                            }
                        )
                        
                        renewed_count += 1
                        logger.info(f"Подписка {locked_subscription.id} продлена до {new_end_date}")
                        
                    else:
                        # НЕУДАЧНЫЙ ПЛАТЕЖ
                        locked_subscription.status = 'pending_renewal'
                        locked_subscription.save()
                        
                        Transaction.objects.create(
                            user=locked_subscription.user,
                            subscription=locked_subscription,
                            amount=locked_subscription.plan.price,
                            transaction_type='subscription_renewal',
                            status='failed',
                            description=f'Ошибка автоматического продления: {payment_result["message"]}',
                            payment_data=payment_result
                        )
                        
                        Notification.objects.create(
                            user=locked_subscription.user,
                            notification_type='payment_failed',
                            title='Ошибка продления подписки',
                            message=f'Не удалось автоматически продлить подписку "{locked_subscription.plan.name}". Причина: {payment_result["message"]}',
                            data={
                                'subscription_id': locked_subscription.id,
                                'error': payment_result['message']
                            }
                        )
                        
                        failed_count += 1
                        logger.warning(f"Ошибка продления подписки {locked_subscription.id}: {payment_result['message']}")
            
            except Exception as e:
                logger.error(f"Ошибка при обработке подписки {subscription.id}: {e}", exc_info=True)
                failed_count += 1
        
        logger.info(f"=== РЕЗУЛЬТАТЫ ===")
        logger.info(f"Успешно продлено: {renewed_count}")
        logger.info(f"Неудачных попыток: {failed_count}")
        
        return {
            'task': 'check_subscription_renewals',
            'timestamp': timezone.now().isoformat(),
            'renewed': renewed_count,
            'failed': failed_count,
            'total_processed': renewed_count + failed_count
        }
        
    except Exception as e:
        logger.error(f"Критическая ошибка в фоновой задаче: {e}", exc_info=True)
        raise

@background(schedule=300)  # запуск каждые 5 мин
def send_expiration_notifications():
    """
    Отправка уведомлений о скором истечении подписки.
    """
    logger.info("=== ЗАПУСК ФОНОВОЙ ЗАДАЧИ: УВЕДОМЛЕНИЯ ОБ ИСТЕЧЕНИИ ===")
    
    try:
        # Подписки, которые истекают через 3 дня
        notification_date = timezone.now() + timedelta(days=3)
        
        subscriptions = UserSubscription.objects.filter(
            status='active',
            end_date__lte=notification_date,
            end_date__gt=timezone.now(),
            auto_renew=True
        ).select_related('user', 'plan')
        
        notifications_sent = 0
        
        for subscription in subscriptions:
            days_left = (subscription.end_date - timezone.now()).days
            
            Notification.objects.create(
                user=subscription.user,
                notification_type='subscription_expiring',
                title='Подписка скоро истекает',
                message=f'Ваша подписка "{subscription.plan.name}" истекает через {days_left} дней ({subscription.end_date.strftime("%d.%m.%Y")})',
                data={
                    'subscription_id': subscription.id,
                    'days_left': days_left,
                    'expiration_date': subscription.end_date.isoformat()
                }
            )
            
            notifications_sent += 1
            logger.info(f"Уведомление отправлено для подписки {subscription.id}, осталось дней: {days_left}")
        
        logger.info(f"Отправлено уведомлений: {notifications_sent}")
        
        return {
            'task': 'send_expiration_notifications',
            'notifications_sent': notifications_sent,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка в задаче отправки уведомлений: {e}", exc_info=True)
        return {'error': str(e)}

@background(schedule=600)  # запуск каждые 10 мин
def retry_failed_payments():
    """
    Повтор неудачных платежей за продление.
    """
    logger.info("=== ЗАПУСК ФОНОВОЙ ЗАДАЧИ: ПОВТОР НЕУДАЧНЫХ ПЛАТЕЖЕЙ ===")
    
    try:
        # Находим подписки с неудачными платежами за последние 2 дня
        retry_date = timezone.now() - timedelta(days=2)
        
        subscriptions = UserSubscription.objects.filter(
            status='pending_renewal',
            updated_at__gte=retry_date,
            auto_renew=True
        ).select_related('user', 'plan')
        
        retried_count = 0
        successful_count = 0
        
        for subscription in subscriptions:
            try:
                with db_transaction.atomic():
                    locked_subscription = UserSubscription.objects.select_for_update().get(id=subscription.id)
                    
                    if locked_subscription.status == 'pending_renewal':
                        logger.info(f"Повторная попытка платежа для подписки {locked_subscription.id}")
                        
                        payment_result = FakePaymentGateway.process_payment(
                            amount=float(locked_subscription.plan.price),
                            user_id=locked_subscription.user.id,
                            description=f"Повторная попытка оплаты: {locked_subscription.plan.name}"
                        )
                        
                        if payment_result['success']:
                            # Успешный платеж
                            new_end_date = locked_subscription.end_date + timedelta(days=locked_subscription.plan.duration_days)
                            locked_subscription.end_date = new_end_date
                            locked_subscription.status = 'active'
                            locked_subscription.save()
                            
                            Transaction.objects.create(
                                user=locked_subscription.user,
                                subscription=locked_subscription,
                                amount=locked_subscription.plan.price,
                                transaction_type='subscription_renewal',
                                status='completed',
                                description='Повторная успешная оплата подписки',
                                payment_data=payment_result
                            )
                            
                            Notification.objects.create(
                                user=locked_subscription.user,
                                notification_type='payment_success',
                                title='Платеж выполнен',
                                message=f'Платеж за подписку "{locked_subscription.plan.name}" успешно выполнен после повторной попытки',
                                data={
                                    'subscription_id': locked_subscription.id,
                                    'new_end_date': new_end_date.isoformat()
                                }
                            )
                            
                            successful_count += 1
                            logger.info(f"Успешный повторный платеж для подписки {locked_subscription.id}")
                        
                        retried_count += 1
            
            except Exception as e:
                logger.error(f"Ошибка при повторной попытке платежа {subscription.id}: {e}")
                continue
        
        logger.info(f"=== РЕЗУЛЬТАТЫ ПОВТОРНЫХ ПОПЫТОК ===")
        logger.info(f"Обработано: {retried_count}")
        logger.info(f"Успешно: {successful_count}")
        
        return {
            'task': 'retry_failed_payments',
            'retried': retried_count,
            'successful': successful_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка в задаче повторных попыток: {e}", exc_info=True)
        return {'error': str(e)}