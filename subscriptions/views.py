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
from users.models import Notification
from datetime import timedelta

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
        
# class RefundRequestView(generics.CreateAPIView):
#     permission_classes = [permissions.IsAuthenticated]
    
#     def post(self, request, *args, **kwargs):
#         transaction_id = request.data.get('transaction_id')
        
#         try:
#             transaction = Transaction.objects.get(
#                 id=transaction_id,
#                 user=request.user,
#                 status='completed',
#                 transaction_type__in=['subscription_purchase', 'subscription_renewal']
#             )
            
#             # Проверяем, что прошло не более 24 часов
#             time_since_purchase = timezone.now() - transaction.created_at
#             if time_since_purchase.total_seconds() > 24 * 3600:
#                 return Response(
#                     {'error': 'Возврат возможен только в течение 24 часов после покупки'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             # Выполняем возврат через платежную систему
#             refund_result = FakePaymentGateway.refund_payment(
#                 original_transaction_id=transaction.payment_data.get('transaction_id'),
#                 amount=float(transaction.amount)
#             )
            
#             if refund_result['success']:
#                 # Создаем транзакцию возврата
#                 refund_transaction = Transaction.objects.create(
#                     user=request.user,
#                     subscription=transaction.subscription,
#                     amount=transaction.amount,
#                     transaction_type='refund',
#                     status='completed',
#                     description=f'Возврат средств по транзакции {transaction.id}',
#                     payment_data=refund_result
#                 )
                
#                 # Отменяем подписку если есть
#                 if transaction.subscription:
#                     subscription = transaction.subscription
#                     subscription.status = 'canceled'
#                     subscription.save()
                
#                 # Создаем уведомление
#                 Notification.objects.create(
#                     user=request.user,
#                     notification_type='refund_processed',
#                     title='Возврат средств',
#                     message=f'Возврат средств в размере {transaction.amount} RUB успешно обработан',
#                     data={'transaction_id': refund_transaction.id}
#                 )
                
#                 return Response({
#                     'success': True,
#                     'refund_id': refund_transaction.id,
#                     'amount': transaction.amount
#                 })
#             else:
#                 return Response({
#                     'error': f'Ошибка возврата: {refund_result["message"]}'
#                 }, status=status.HTTP_400_BAD_REQUEST)
                
#         except Transaction.DoesNotExist:
#             return Response(
#                 {'error': 'Транзакция не найдена или не подлежит возврату'},
#                 status=status.HTTP_404_NOT_FOUND
#             )

class RefundRequestView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def calculate_refund_amount(self, transaction, subscription):
        """
        расчет суммы возврата:
        - Полный возврат в первые 3 дня
        - Пропорциональный возврат после 3 дней
        - Без возврата после окончания подписки
        """
        time_since_purchase = timezone.now() - transaction.created_at
        days_since_purchase = time_since_purchase.days
        
        # Если подписка уже закончилась - возврат невозможен
        if subscription and subscription.end_date < timezone.now():
            return 0, "Возврат невозможен: подписка уже закончилась"
        
        # Полный возврат в первые 3 дня
        if days_since_purchase <= 3:
            return float(transaction.amount), "Полный возврат (в течение 3 дней)"
        
        # Пропорциональный возврат после 3 дней
        if subscription:
            # Расчет использованного времени
            total_duration = (subscription.end_date - subscription.start_date).days
            days_used = (timezone.now() - subscription.start_date).days
            
            if total_duration > 0 and days_used < total_duration:
                # Возвращаем пропорционально неиспользованному времени
                days_unused = total_duration - days_used
                refund_percentage = days_unused / total_duration
                
                # Минимальный возврат - 50% от оставшейся суммы
                min_refund_percentage = 0.5
                if refund_percentage < min_refund_percentage:
                    refund_percentage = min_refund_percentage
                
                refund_amount = float(transaction.amount) * refund_percentage
                return refund_amount, f"Пропорциональный возврат ({int(refund_percentage*100)}% за {days_unused} неиспользованных дней)"
        
        # По умолчанию - без возврата
        return 0, "Возврат невозможен по истечении срока"
    
    def post(self, request, *args, **kwargs):
        transaction_id = request.data.get('transaction_id')
        refund_reason = request.data.get('reason', '')
        
        try:
            with db_transaction.atomic():
                # Блокируем транзакцию для предотвращения повторных возвратов
                transaction = Transaction.objects.select_for_update().get(
                    id=transaction_id,
                    user=request.user,
                    status='completed',
                    transaction_type__in=['subscription_purchase', 'subscription_renewal']
                )
                
                # Проверяем, не был ли уже сделан возврат
                existing_refund = Transaction.objects.filter(
                    user=request.user,
                    subscription=transaction.subscription,
                    transaction_type='refund',
                    status='completed'
                ).exists()
                
                if existing_refund:
                    return Response(
                        {'error': 'По этой транзакции уже был выполнен возврат'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Получаем подписку если есть
                subscription = transaction.subscription
                
                # Рассчитываем сумму возврата
                refund_amount, refund_reason_text = self.calculate_refund_amount(transaction, subscription)
                
                if refund_amount <= 0:
                    return Response(
                        {
                            'error': refund_reason_text,
                            'details': 'Для возврата средств обратитесь в поддержку'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Логируем запрос на возврат
                logger.info(
                    f"Refund request: transaction={transaction.id}, "
                    f"amount={transaction.amount}, "
                    f"calculated_refund={refund_amount}, "
                    f"reason={refund_reason_text}, "
                    f"user_reason={refund_reason}"
                )
                
                # Выполняем возврат через платежную систему
                refund_result = FakePaymentGateway.refund_payment(
                    original_transaction_id=transaction.payment_data.get('transaction_id'),
                    amount=refund_amount
                )
                
                if refund_result['success']:
                    # Создаем транзакцию возврата
                    refund_transaction = Transaction.objects.create(
                        user=request.user,
                        subscription=transaction.subscription,
                        amount=refund_amount,
                        transaction_type='refund',
                        status='completed',
                        description=f'Возврат средств. {refund_reason_text}. Причина от пользователя: {refund_reason}',
                        payment_data=refund_result
                    )
                    
                    # Обновляем подписку если есть
                    if transaction.subscription:
                        subscription = transaction.subscription
                        
                        # Если это полный возврат - отменяем подписку
                        if refund_amount >= float(transaction.amount) * 0.95:  # 95% для учета округления
                            subscription.status = 'canceled'
                            subscription.save()
                            
                            # Создаем уведомление об отмене
                            Notification.objects.create(
                                user=request.user,
                                notification_type='subscription_canceled',
                                title='Подписка отменена',
                                message=f'Подписка "{subscription.plan.name}" отменена в связи с возвратом средств',
                                data={
                                    'subscription_id': subscription.id,
                                    'refund_amount': refund_amount
                                }
                            )
                        else:
                            # Частичный возврат - уменьшаем срок подписки
                            # Рассчитываем на сколько дней уменьшить
                            refund_percentage = refund_amount / float(transaction.amount)
                            days_to_reduce = int(subscription.plan.duration_days * refund_percentage)
                            
                            if days_to_reduce > 0:
                                subscription.end_date = subscription.end_date - timedelta(days=days_to_reduce)
                                subscription.save()
                                
                                # Создаем уведомление об изменении срока
                                Notification.objects.create(
                                    user=request.user,
                                    notification_type='subscription_modified',
                                    title='Срок подписки изменен',
                                    message=f'Срок подписки "{subscription.plan.name}" уменьшен на {days_to_reduce} дней в связи с частичным возвратом',
                                    data={
                                        'subscription_id': subscription.id,
                                        'refund_amount': refund_amount,
                                        'days_reduced': days_to_reduce,
                                        'new_end_date': subscription.end_date.isoformat()
                                    }
                                )
                    
                    # Создаем уведомление о возврате
                    Notification.objects.create(
                        user=request.user,
                        notification_type='refund_processed',
                        title='Возврат средств',
                        message=f'Возврат средств в размере {refund_amount:.2f} RUB успешно обработан. {refund_reason_text}',
                        data={
                            'transaction_id': refund_transaction.id,
                            'refund_amount': refund_amount,
                            'original_amount': float(transaction.amount),
                            'refund_percentage': (refund_amount / float(transaction.amount)) * 100 if transaction.amount > 0 else 0
                        }
                    )
                    
                    return Response({
                        'success': True,
                        'refund_id': refund_transaction.id,
                        'refund_amount': refund_amount,
                        'original_amount': transaction.amount,
                        'refund_reason': refund_reason_text,
                        'message': 'Возврат средств успешно обработан'
                    })
                else:
                    # Ошибка возврата в платежной системе
                    logger.error(f"Payment gateway refund failed: {refund_result}")
                    
                    # Создаем транзакцию с ошибкой
                    Transaction.objects.create(
                        user=request.user,
                        subscription=transaction.subscription,
                        amount=refund_amount,
                        transaction_type='refund',
                        status='failed',
                        description=f'Ошибка возврата: {refund_result["message"]}',
                        payment_data=refund_result
                    )
                    
                    return Response({
                        'error': f'Ошибка возврата в платежной системе: {refund_result["message"]}',
                        'details': 'Пожалуйста, обратитесь в поддержку'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
        except Transaction.DoesNotExist:
            return Response(
                {'error': 'Транзакция не найдена или не подлежит возврату'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Unexpected error in refund processing: {e}", exc_info=True)
            return Response(
                {'error': 'Внутренняя ошибка сервера при обработке возврата'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

class RefundPolicyView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        policy_info = {
            'full_refund_days': 3,
            'partial_refund_enabled': True,
            'max_refund_days': 30,
            'description': """
            Политика возврата средств:
            
            1. Полный возврат - в течение 3 дней после покупки
            2. Частичный возврат - с 4-го дня до окончания подписки
               (возвращается сумма пропорционально неиспользованному времени)
            3. Минимальный возврат - 50% от стоимости неиспользованного периода
            4. Возврат невозможен после окончания срока действия подписки
            
            Для запроса возврата выберите транзакцию и укажите причину.
            """,
            'contact_support': 'Если у вас особый случай, обратитесь в поддержку: support@example.com'
        }
        
        return Response(policy_info)
    

class TestRenewSubscriptionView(generics.GenericAPIView):
    """Тестовое продление подписки"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, subscription_id):
        try:
            subscription = UserSubscription.objects.get(
                id=subscription_id,
                user=request.user
            )
            
            # Имитируем платеж
            from .payment_gateway import FakePaymentGateway
            
            payment_result = FakePaymentGateway.process_payment(
                amount=float(subscription.plan.price),
                user_id=request.user.id,
                description=f"Тестовое продление: {subscription.plan.name}"
            )
            
            if payment_result['success']:
                # Продлеваем подписку
                new_end_date = timezone.now() + timedelta(days=subscription.plan.duration_days)
                subscription.end_date = new_end_date
                subscription.status = 'active'
                subscription.save()
                
                # Создаем транзакцию
                Transaction.objects.create(
                    user=request.user,
                    subscription=subscription,
                    amount=subscription.plan.price,
                    transaction_type='subscription_renewal',
                    status='completed',
                    description='Тестовое продление (ручное)',
                    payment_data=payment_result
                )
                
                return Response({
                    'success': True,
                    'message': f'Подписка продлена до {new_end_date}',
                    'new_end_date': new_end_date
                })
            else:
                return Response({
                    'success': False,
                    'message': f'Ошибка платежа: {payment_result["message"]}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except UserSubscription.DoesNotExist:
            return Response({'error': 'Подписка не найдена'}, status=status.HTTP_404_NOT_FOUND)

class UpdateEndDateView(generics.GenericAPIView):
    """Обновление даты окончания для тестирования"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, subscription_id):
        try:
            subscription = UserSubscription.objects.get(
                id=subscription_id,
                user=request.user
            )
            
            minutes = request.data.get('minutes', 5)
            
            new_end_date = timezone.now() + timedelta(minutes=minutes)
            subscription.end_date = new_end_date
            subscription.save()
            
            return Response({
                'success': True,
                'message': f'Дата окончания обновлена: {new_end_date}',
                'new_end_date': new_end_date.isoformat()
            })
            
        except UserSubscription.DoesNotExist:
            return Response({'error': 'Подписка не найдена'}, status=status.HTTP_404_NOT_FOUND)

class ManualRenewalCheckView(generics.GenericAPIView):
    """Ручная проверка продления"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        from datetime import timedelta
        
        renewal_date = timezone.now() + timedelta(hours=24)
        
        subscriptions = UserSubscription.objects.filter(
            user=request.user,
            status='active',
            auto_renew=True,
            end_date__lte=renewal_date,
            end_date__gt=timezone.now()
        )
        
        results = []
        
        for subscription in subscriptions:
            from .payment_gateway import FakePaymentGateway
            
            payment_result = FakePaymentGateway.process_payment(
                amount=float(subscription.plan.price),
                user_id=request.user.id,
                description=f"Ручное продление: {subscription.plan.name}"
            )
            
            if payment_result['success']:
                new_end_date = subscription.end_date + timedelta(days=subscription.plan.duration_days)
                subscription.end_date = new_end_date
                subscription.save()
                
                Transaction.objects.create(
                    user=request.user,
                    subscription=subscription,
                    amount=subscription.plan.price,
                    transaction_type='subscription_renewal',
                    status='completed',
                    description='Ручное продление',
                    payment_data=payment_result
                )
                
                results.append({
                    'subscription_id': subscription.id,
                    'status': 'renewed',
                    'new_end_date': new_end_date.isoformat()
                })
            else:
                results.append({
                    'subscription_id': subscription.id,
                    'status': 'failed',
                    'error': payment_result['message']
                })
        
        return Response({
            'checked': len(subscriptions),
            'renewed': len([r for r in results if r['status'] == 'renewed']),
            'failed': len([r for r in results if r['status'] == 'failed']),
            'results': results
        })