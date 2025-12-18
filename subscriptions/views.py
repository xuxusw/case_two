from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db import transaction as db_transaction
from decimal import Decimal
import logging

from .models import SubscriptionPlan, UserSubscription, Transaction, PromoCode
from .serializers import (
    SubscriptionPlanSerializer, UserSubscriptionSerializer,
    TransactionSerializer, PromoCodeSerializer, SubscriptionPurchaseSerializer
)
from .payment_gateway import FakePaymentGateway
from users.models import User

logger = logging.getLogger(__name__)

class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]

class UserSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        if subscription.status != 'active':
            return Response({'error': 'Только активные подписки можно отменить'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        subscription.status = 'canceled'
        subscription.auto_renew = False
        subscription.save()
        
        # запись в истории
        Transaction.objects.create(
            user=request.user,
            subscription=subscription,
            amount=0,
            transaction_type='subscription_purchase',
            status='completed',
            description='Подписка отменена пользователем'
        )
        
        return Response({'status': 'Подписка отменена'})
    
    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        subscription = self.get_object()
        if subscription.status not in ['active', 'expired']:
            return Response({'error': 'Невозможно продлить эту подписку'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # сюда нужна логика продления
        return Response({'message': 'Функция продления будет позже'})

class PurchaseSubscriptionView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubscriptionPurchaseSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        plan = data['plan']
        promo = data.get('promo')
        user = request.user
        
        # цена с учетом промокода
        price = plan.price
        discount_percent = 0
        
        if promo:
            discount_percent = promo.discount_percent
            price = plan.price * (100 - discount_percent) / 100
        
        with db_transaction.atomic():
            # создание подписки в статусе pending
            subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                status='pending'
            )
            
            # создание транзакции
            transaction = Transaction.objects.create(
                user=user,
                subscription=subscription,
                amount=price,
                transaction_type='subscription_purchase',
                status='pending',
                description=f'Покупка подписки {plan.name}'
            )
            
            # Обработка платежа
            payment_result = FakePaymentGateway.process_payment(
                amount=float(price),
                user_id=user.id,
                description=f"Подписка: {plan.name}"
            )
            
            # обновление статуса транзакции
            transaction.payment_data = payment_result
            if payment_result['success']:
                transaction.status = 'completed'
                
                # активация подписки
                subscription.status = 'active'
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timezone.timedelta(days=plan.duration_days)
                
                # Увеличиваем счетчик использования промокода
                if promo:
                    promo.used_count += 1
                    promo.save()
                
                subscription.save()
                transaction.save()
                
                logger.info(f"Подписка активирована для пользователя {user.username}, сумма: {price}")
                
                return Response({
                    'success': True,
                    'message': 'Подписка успешно оформлена',
                    'subscription_id': subscription.id,
                    'transaction_id': transaction.id,
                    'end_date': subscription.end_date
                }, status=status.HTTP_201_CREATED)
            else:
                transaction.status = 'failed'
                subscription.status = 'expired'  # или pending для retry
                subscription.save()
                transaction.save()
                
                logger.error(f"Ошибка платежа для пользователя {user.username}: {payment_result['message']}")
                
                return Response({
                    'success': False,
                    'message': f'Ошибка платежа: {payment_result["message"]}',
                    'transaction_id': transaction.id
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

class PromoCodeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PromoCode.objects.filter(is_active=True)
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserBalanceView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        # Здесь надо бы проверку баланса в платежной системе
        # Но пока - баланс из модели User
        payment_balance = FakePaymentGateway.check_balance(user.id)
        
        return Response({
            'user_balance': float(user.balance),
            'payment_gateway_balance': payment_balance['balance'],
            'currency': 'RUB'
        })