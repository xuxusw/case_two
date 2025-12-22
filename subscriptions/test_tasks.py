from django.utils import timezone
from datetime import timedelta
import logging
from .models import UserSubscription, Transaction, SubscriptionPlan
from users.models import User, Notification

logger = logging.getLogger(__name__)

def test_renewal_manually():
    """Ручной тест функции продления"""
    print("=== ТЕСТ АВТОМАТИЧЕСКОГО ПРОДЛЕНИЯ ===")
    
    # Создаем тестовые данные 
    try:
        user = User.objects.get(username="testuser")
    except User.DoesNotExist:
        user = User.objects.create_user(username="testuser", password="testpass")
    
    try:
        plan = SubscriptionPlan.objects.first()
        if not plan:
            plan = SubscriptionPlan.objects.create(
                name="Тестовый план",
                price=100,
                duration_days=7
            )
    except:
        plan = SubscriptionPlan.objects.create(
            name="Тестовый план",
            price=100,
            duration_days=7
        )
    
    # Создаем подписку, которая заканчивается сегодня
    subscription, created = UserSubscription.objects.get_or_create(
        user=user,
        plan=plan,
        defaults={
            'status': 'active',
            'start_date': timezone.now() - timedelta(days=6),
            'end_date': timezone.now() + timedelta(hours=1),  # Заканчивается через 1 час
            'auto_renew': True
        }
    )
    
    print(f"Подписка создана: ID={subscription.id}")
    print(f"Статус: {subscription.status}")
    print(f"Окончание: {subscription.end_date}")
    print(f"Автопродление: {subscription.auto_renew}")
    
    # Вызываем логику продления
    from .payment_gateway import FakePaymentGateway
    
    print("\n=== ИМИТАЦИЯ ПЛАТЕЖА ===")
    payment_result = FakePaymentGateway.process_payment(
        amount=float(plan.price),
        user_id=user.id,
        description=f"Тестовое продление: {plan.name}"
    )
    
    print(f"Результат платежа: {payment_result['success']}")
    print(f"Сообщение: {payment_result['message']}")
    
    if payment_result['success']:
        # Продлеваем подписку
        new_end_date = subscription.end_date + timedelta(days=plan.duration_days)
        subscription.end_date = new_end_date
        subscription.save()
        
        # Создаем транзакцию
        Transaction.objects.create(
            user=user,
            subscription=subscription,
            amount=plan.price,
            transaction_type='subscription_renewal',
            status='completed',
            description='Тестовое продление',
            payment_data=payment_result
        )
        
        # Создаем уведомление
        Notification.objects.create(
            user=user,
            notification_type='payment_success',
            title='Тестовое уведомление',
            message=f'Подписка продлена до {new_end_date}',
            data={'test': True}
        )
        
        print(f"\nПодписка продлена до: {new_end_date}")
        print(f"Транзакция создана")
        print(f"Уведомление создано")
    else:
        print(f"\nПлатеж не прошел: {payment_result['message']}")
    
    return subscription