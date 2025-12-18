from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan, PromoCode
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Создает тестовые данные для подписок'
    
    def handle(self, *args, **kwargs):
        # Планы подписок
        plans = [
            {'name': 'Базовый', 'description': 'Доступ к базовым функциям', 'price': 299, 'duration_days': 30},
            {'name': 'Продвинутый', 'description': 'Расширенные возможности', 'price': 599, 'duration_days': 30},
            {'name': 'Профессиональный', 'description': 'Полный доступ ко всем функциям', 'price': 999, 'duration_days': 30},
            {'name': 'Годовой', 'description': 'Экономия 20% при оплате за год', 'price': 9599, 'duration_days': 365},
        ]
        
        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создан план: {plan.name}'))
        
        # Промокоды
        promos = [
            {'code': 'WELCOME10', 'discount_percent': 10, 'max_uses': 100, 
             'valid_from': timezone.now(), 'valid_to': timezone.now() + timedelta(days=365),
             'description': 'Скидка 10% для новых пользователей'},
            {'code': 'SUMMER2025', 'discount_percent': 20, 'max_uses': 50,
             'valid_from': timezone.now(), 'valid_to': timezone.now() + timedelta(days=90),
             'description': 'Летняя акция'},
        ]
        
        for promo_data in promos:
            promo, created = PromoCode.objects.get_or_create(
                code=promo_data['code'],
                defaults=promo_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создан промокод: {promo.code}'))
        
        self.stdout.write(self.style.SUCCESS('Тестовые данные созданы успешно'))