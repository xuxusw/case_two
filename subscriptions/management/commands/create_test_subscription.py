from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from subscriptions.models import UserSubscription, SubscriptionPlan
from users.models import User

class Command(BaseCommand):
    help = 'Создает тестовую подписку для проверки автоматического продления'
    
    def handle(self, *args, **options):
        self.stdout.write("=== СОЗДАНИЕ ТЕСТОВОЙ ПОДПИСКИ ===")
        
        # Получаем или создаем пользователя
        try:
            user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            user = User.objects.create_user(
                username='testuser',
                password='testpass123',
                email='test@example.com'
            )
            self.stdout.write(f"Создан пользователь: {user.username}")
        
        # Получаем или создаем план
        try:
            plan = SubscriptionPlan.objects.first()
            if not plan:
                plan = SubscriptionPlan.objects.create(
                    name='Тестовый план',
                    description='Для тестирования автоматического продления',
                    price=299.00,
                    duration_days=7,
                    is_active=True
                )
        except:
            plan = SubscriptionPlan.objects.create(
                name='Тестовый план',
                description='Для тестирования автоматического продления',
                price=299.00,
                duration_days=7,
                is_active=True
            )
        
        # Создаем подписку, которая заканчивается через 1 час
        subscription, created = UserSubscription.objects.get_or_create(
            user=user,
            plan=plan,
            defaults={
                'status': 'active',
                'start_date': timezone.now() - timedelta(days=6),
                'end_date': timezone.now() + timedelta(minutes=30),  # Заканчивается через 30 минут
                'auto_renew': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"Создана тестовая подписка:"))
        else:
            subscription.end_date = timezone.now() + timedelta(minutes=30)
            subscription.status = 'active'
            subscription.auto_renew = True
            subscription.save()
            self.stdout.write(self.style.SUCCESS(f"Обновлена тестовая подписка:"))
        
        self.stdout.write(f"   ID подписки: {subscription.id}")
        self.stdout.write(f"   Пользователь: {user.username}")
        self.stdout.write(f"   План: {plan.name}")
        self.stdout.write(f"   Статус: {subscription.status}")
        self.stdout.write(f"   Окончание: {subscription.end_date}")
        self.stdout.write(f"   Автопродление: {subscription.auto_renew}")
        self.stdout.write(f"   Осталось минут: {(subscription.end_date - timezone.now()).seconds // 60}")
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("Теперь подписка будет автоматически продлена через 30 минут!")
        self.stdout.write("Для ускорения тестирования можно изменить время в коде.")