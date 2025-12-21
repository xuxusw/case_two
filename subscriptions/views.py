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
from .email_service import send_test_email
from users.serializers import NotificationSerializer

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
        
        old_status = subscription.status
        subscription.status = 'canceled'
        subscription.auto_renew = False
        subscription.save()
        
        # Запись в истории
        Transaction.objects.create(
            user=request.user,
            subscription=subscription,
            amount=0,
            transaction_type='subscription_cancel',
            status='completed',
            description='Подписка отменена пользователем'
        )
        
        # Создаем уведомление об отмене
        try:
            Notification.objects.create(
                user=request.user,
                notification_type='subscription_canceled',
                title='Подписка отменена',
                message=f'Подписка "{subscription.plan.name}" отменена. Статус изменен: {old_status} -> {subscription.status}',
                is_read=False,
                data={
                    'subscription_id': subscription.id,
                    'plan_name': subscription.plan.name,
                    'old_status': old_status,
                    'new_status': subscription.status,
                    'end_date': subscription.end_date.isoformat() if subscription.end_date else None
                }
            )
            
            # Логируем email уведомление
            logger.info(f"EMAIL: Отправка уведомления об отмене подписки пользователю {request.user.email}")
            logger.info(f"EMAIL Тема: Подписка '{subscription.plan.name}' отменена")
            logger.info(f"EMAIL Сообщение: Ваша подписка '{subscription.plan.name}' была отменена.")
            
        except Exception as e:
            logger.error(f"Ошибка при создании уведомления: {e}")
        
        return Response({'status': 'Подписка отменена'})
    
    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        subscription = self.get_object()
        if subscription.status not in ['active', 'expired']:
            return Response({'error': 'Невозможно продлить эту подписку'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': 'Функция продления будет позже'})
    
    # ИСПРАВЛЕНИЕ: Добавлен url_path для корректной работы с роутером
    @action(detail=True, methods=['patch'], url_path='toggle-auto-renew')
    def toggle_auto_renew(self, request, pk=None):
        """Включение/выключение автопродления"""
        subscription = self.get_object()
        
        # Проверяем, активна ли подписка
        if subscription.status != 'active':
            return Response({
                'error': 'Автопродление можно менять только для активных подписок'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        auto_renew = request.data.get('auto_renew')
        if auto_renew is None:
            # Если auto_renew не указан, просто инвертируем текущее значение
            subscription.auto_renew = not subscription.auto_renew
        else:
            subscription.auto_renew = bool(auto_renew)
        
        old_value = not subscription.auto_renew if auto_renew is None else bool(auto_renew)
        subscription.save()
        
        # Создаем уведомление
        status_text = "включено" if subscription.auto_renew else "выключено"
        Notification.objects.create(
            user=request.user,
            notification_type='info',
            title='Настройки автопродления изменены',
            message=f'Автоматическое продление для подписки "{subscription.plan.name}" {status_text}',
            data={
                'subscription_id': subscription.id,
                'plan_name': subscription.plan.name,
                'auto_renew': subscription.auto_renew,
                'old_auto_renew': old_value
            }
        )
        
        logger.info(f"Пользователь {request.user.username} изменил автопродление "
                    f"подписки {subscription.id}: {old_value} -> {subscription.auto_renew}")
        
        return Response({
            'success': True,
            'message': f'Автопродление {status_text}',
            'auto_renew': subscription.auto_renew,
            'subscription_status': subscription.status
        })


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
        
        # Цена с учетом промокода
        price = plan.price
        discount_percent = 0
        
        if promo:
            discount_percent = promo.discount_percent
            price = plan.price * (100 - discount_percent) / 100
        
        # Проверяем, достаточно ли средств у пользователя
        if user.balance < price:
            return Response({
                'success': False,
                'message': f'Недостаточно средств на балансе. Необходимо: {price} руб., доступно: {user.balance} руб.'
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        with db_transaction.atomic():
            # Создание подписки в статусе pending
            subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                status='pending'
            )
            
            # Создание транзакции
            transaction = Transaction.objects.create(
                user=user,
                subscription=subscription,
                amount=price,
                transaction_type='subscription_purchase',
                status='pending',
                description=f'Покупка подписки {plan.name}' + (f' (скидка {discount_percent}%)' if promo else '')
            )
            
            # Обработка платежа через фейковый шлюз
            payment_result = FakePaymentGateway.process_payment(
                amount=float(price),
                user_id=user.id,
                description=f"Подписка: {plan.name}"
            )
            
            # Обновление статуса транзакции
            transaction.payment_data = payment_result
            if payment_result['success']:
                # Списание средств с баланса пользователя
                user.balance -= price
                user.save()
                
                transaction.status = 'completed'
                
                # Активация подписки
                subscription.status = 'active'
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timezone.timedelta(days=plan.duration_days)
                
                # Увеличиваем счетчик использования промокода
                if promo:
                    promo.used_count += 1
                    promo.save()
                
                subscription.save()
                transaction.save()
                
                # Создаем уведомление об успешной покупке
                try:
                    Notification.objects.create(
                        user=user,
                        notification_type='payment_success',
                        title='Подписка оформлена',
                        message=f'Вы успешно подписались на тариф "{plan.name}" за {price} руб. Подписка активна до {subscription.end_date.strftime("%d.%m.%Y")}',
                        is_read=False,
                        data={
                            'subscription_id': subscription.id,
                            'plan_name': subscription.plan.name,
                            'amount': str(price),
                            'end_date': subscription.end_date.isoformat(),
                            'discount_percent': discount_percent if promo else 0
                        }
                    )
                    
                    # Логируем email уведомление
                    logger.info("=" * 60)
                    logger.info("EMAIL УВЕДОМЛЕНИЕ (симуляция):")
                    logger.info(f"Кому: {user.email}")
                    logger.info(f"Тема: Подписка на {plan.name} оформлена!")
                    logger.info(f"Сообщение: Вы успешно подписались на тариф '{plan.name}'")
                    logger.info(f"Сумма: {price} руб." + (f" (скидка {discount_percent}%)" if promo else ""))
                    logger.info(f"Статус: Активна до {subscription.end_date.strftime('%d.%m.%Y')}")
                    logger.info(f"Новый баланс: {user.balance} руб.")
                    logger.info("=" * 60)
                    
                except Exception as e:
                    logger.error(f"Ошибка при создании уведомления: {e}")
                
                logger.info(f"Подписка активирована для пользователя {user.username}, сумма: {price}")
                
                return Response({
                    'success': True,
                    'message': 'Подписка успешно оформлена',
                    'subscription_id': subscription.id,
                    'transaction_id': transaction.id,
                    'end_date': subscription.end_date,
                    'new_balance': float(user.balance)
                }, status=status.HTTP_201_CREATED)
            else:
                transaction.status = 'failed'
                subscription.status = 'expired'
                subscription.save()
                transaction.save()
                
                # Создаем уведомление об ошибке
                try:
                    Notification.objects.create(
                        user=user,
                        notification_type='payment_failed',
                        title='Ошибка оплаты',
                        message=f'Не удалось оплатить подписку "{plan.name}". Причина: {payment_result["message"]}',
                        is_read=False,
                        data={
                            'plan_name': plan.name,
                            'amount': str(price),
                            'error': payment_result["message"]
                        }
                    )
                    
                    logger.error(f"Ошибка платежа для пользователя {user.username}: {payment_result['message']}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при создании уведомления об ошибке: {e}")
                
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
        payment_balance = FakePaymentGateway.check_balance(user.id)
        
        return Response({
            'user_balance': float(user.balance),
            'payment_gateway_balance': payment_balance['balance'],
            'currency': 'RUB'
        })


class NotificationView(generics.ListAPIView):
    """Получить все уведомления пользователя"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        notifications = self.get_queryset()
        data = []
        
        for notification in notifications:
            data.append({
                'id': notification.id,
                'notification_type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'data': notification.data,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat()
            })
        
        return Response(data)


class MarkNotificationReadView(generics.GenericAPIView):
    """Пометить уведомление как прочитанное"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.is_read = True
            notification.save()
            
            return Response({'success': True})
            
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Уведомление не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )


class MarkAllNotificationsReadView(generics.GenericAPIView):
    """Пометить все уведомления как прочитанные"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        updated = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'success': True,
            'marked_read': updated
        })


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
                    
                    # Возвращаем средства на баланс пользователя
                    user = request.user
                    user.balance += Decimal(str(refund_amount))
                    user.save()
                    
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
                    try:
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
                        
                        # Логируем email уведомление
                        logger.info(f"EMAIL: Возврат средств пользователю {user.email}")
                        logger.info(f"EMAIL: Сумма возврата: {refund_amount} руб.")
                        logger.info(f"EMAIL: Новый баланс: {user.balance} руб.")
                        
                    except Exception as e:
                        logger.error(f"Ошибка при создании уведомления о возврате: {e}")
                    
                    return Response({
                        'success': True,
                        'refund_id': refund_transaction.id,
                        'refund_amount': refund_amount,
                        'original_amount': transaction.amount,
                        'refund_reason': refund_reason_text,
                        'new_balance': float(user.balance),
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
                transaction = Transaction.objects.create(
                    user=request.user,
                    subscription=subscription,
                    amount=subscription.plan.price,
                    transaction_type='subscription_renewal',
                    status='completed',
                    description='Тестовое продление (ручное)',
                    payment_data=payment_result
                )
                
                # Создаем уведомление
                try:
                    Notification.objects.create(
                        user=request.user,
                        notification_type='payment_success',
                        title='Подписка продлена',
                        message=f'Подписка "{subscription.plan.name}" продлена до {new_end_date.strftime("%d.%m.%Y")}',
                        data={
                            'subscription_id': subscription.id,
                            'plan_name': subscription.plan.name,
                            'new_end_date': new_end_date.isoformat(),
                            'amount': str(subscription.plan.price)
                        }
                    )
                    
                    logger.info(f"EMAIL: Подписка продлена для пользователя {request.user.email}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при создании уведомления о продлении: {e}")
                
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
            
            # Создаем уведомление об изменении даты
            try:
                Notification.objects.create(
                    user=request.user,
                    notification_type='info',
                    title='Дата окончания изменена',
                    message=f'Дата окончания подписки "{subscription.plan.name}" изменена на {new_end_date.strftime("%d.%m.%Y %H:%M")}',
                    data={
                        'subscription_id': subscription.id,
                        'plan_name': subscription.plan.name,
                        'new_end_date': new_end_date.isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"Ошибка при создании уведомления: {e}")
            
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
        # Проверяем права администратора
        if not (request.user.role == 'admin' or request.user.is_superuser):
            return Response(
                {'error': 'Требуются права администратора'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        renewal_date = timezone.now() + timedelta(hours=24)
        
        subscriptions = UserSubscription.objects.filter(
            status='active',
            auto_renew=True,
            end_date__lte=renewal_date,
            end_date__gt=timezone.now()
        ).select_related('user', 'plan')
        
        results = []
        renewed_count = 0
        failed_count = 0
        
        for subscription in subscriptions:
            try:
                # Проверяем баланс пользователя
                if subscription.user.balance < subscription.plan.price:
                    results.append({
                        'subscription_id': subscription.id,
                        'user': subscription.user.username,
                        'plan': subscription.plan.name,
                        'status': 'failed',
                        'error': 'Недостаточно средств на балансе',
                        'message': f'Баланс: {subscription.user.balance}, требуется: {subscription.plan.price}'
                    })
                    failed_count += 1
                    continue
                
                # Имитация платежа
                payment_result = FakePaymentGateway.process_payment(
                    amount=float(subscription.plan.price),
                    user_id=subscription.user.id,
                    description=f"Ручное продление: {subscription.plan.name}"
                )
                
                if payment_result['success']:
                    # Списание средств
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
                        transaction_type='subscription_renewal',
                        status='completed',
                        description='Ручное продление (админ)',
                        payment_data=payment_result
                    )
                    
                    # Создаем уведомление
                    try:
                        Notification.objects.create(
                            user=subscription.user,
                            notification_type='subscription_renewal',
                            title='Подписка продлена',
                            message=f'Ваша подписка "{subscription.plan.name}" автоматически продлена до {new_end_date.strftime("%d.%m.%Y")}',
                            data={
                                'subscription_id': subscription.id,
                                'plan_name': subscription.plan.name,
                                'new_end_date': new_end_date.isoformat(),
                                'amount': str(subscription.plan.price),
                                'new_balance': float(subscription.user.balance)
                            }
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при создании уведомления: {e}")
                    
                    results.append({
                        'subscription_id': subscription.id,
                        'user': subscription.user.username,
                        'plan': subscription.plan.name,
                        'status': 'renewed',
                        'new_end_date': new_end_date.isoformat(),
                        'new_balance': float(subscription.user.balance),
                        'message': 'Успешно продлено'
                    })
                    renewed_count += 1
                    
                else:
                    results.append({
                        'subscription_id': subscription.id,
                        'user': subscription.user.username,
                        'plan': subscription.plan.name,
                        'status': 'failed',
                        'error': payment_result['message'],
                        'message': 'Ошибка платежа'
                    })
                    failed_count += 1
                    
            except Exception as e:
                results.append({
                    'subscription_id': subscription.id,
                    'status': 'error',
                    'error': str(e),
                    'message': 'Исключение при обработке'
                })
                failed_count += 1
        
        return Response({
            'success': True,
            'checked': len(subscriptions),
            'renewed': renewed_count,
            'failed': failed_count,
            'results': results,
            'message': f'Проверено {len(subscriptions)} подписок. Успешно: {renewed_count}, Ошибок: {failed_count}'
        })
        
        
class SendTestEmailView(generics.GenericAPIView):
    """Отправка тестового email"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Проверяем, что пользователь администратор
        if request.user.role != 'admin' and not request.user.is_superuser:
            return Response(
                {'error': 'Требуются права администратора'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        email = request.data.get('email', request.user.email)
        
        try:
            success = send_test_email(email)
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Тестовый email отправлен на {email}'
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Ошибка отправки email'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                'error': f'Ошибка: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            

class AdminSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """API для администраторов (получение всех подписок)"""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Проверяем, что пользователь администратор
        if self.request.user.role != 'admin' and not self.request.user.is_superuser:
            return UserSubscription.objects.none()
        
        return UserSubscription.objects.all().select_related('user', 'plan').order_by('-created_at')


class AdminTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """API для администраторов (получение всех транзакций)"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Проверяем, что пользователь администратор
        if self.request.user.role != 'admin' and not self.request.user.is_superuser:
            return Transaction.objects.none()
        
        return Transaction.objects.all().select_related('user').order_by('-created_at')


class MySubscriptionsView(generics.ListAPIView):
    """Получить все подписки текущего пользователя"""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user).select_related('plan')
    

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра уведомлений пользователя"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        # Возвращаем уведомления только текущего пользователя, сначала новые
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='mark-all-as-read')
    def mark_all_as_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'notifications marked as read'})
    
    @action(detail=True, methods=['post'], url_path='mark-as-read')
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'read'})