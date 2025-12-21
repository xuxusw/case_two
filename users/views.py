from django.shortcuts import render

# Create your views here.

from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate
from django.db import transaction as db_transaction  
from .serializers import RegisterSerializer, UserSerializer, UserBalanceSerializer, DepositSerializer
from .models import User, Notification  
from subscriptions.models import Transaction 
import logging

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
        return Response({'error': 'Неверные учетные данные'}, status=400)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """API для администраторов (получение всех пользователей)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Проверяем, что пользователь администратор
        if self.request.user.role != 'admin' and not self.request.user.is_superuser:
            return User.objects.none()
        
        return User.objects.all().order_by('-date_joined')

class AdminUpdateUserView(generics.GenericAPIView):
    """Изменение данных пользователя администратором"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        # Проверка прав администратора
        if not (request.user.role == 'admin' or request.user.is_superuser):
            return Response(
                {'error': 'Требуются права администратора'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = User.objects.get(id=user_id)
            
            # Обновляем поля
            new_role = request.data.get('role')
            new_balance = request.data.get('balance')
            is_active = request.data.get('is_active')
            
            if new_role and new_role in ['user', 'admin']:
                user.role = new_role
            
            if new_balance is not None:
                try:
                    user.balance = float(new_balance)
                except:
                    return Response({'error': 'Неверный формат баланса'}, status=400)
            
            if is_active is not None:
                user.is_active = bool(is_active)
            
            user.save()
            
            return Response({
                'success': True,
                'message': f'Пользователь {user.username} обновлен',
                'user': UserSerializer(user).data
            })
            
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=404)

# ========== Функции для работы с балансом ==========

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_balance(request):
    """Получить баланс пользователя (быстрый запрос)"""
    try:
        # Проверяем, есть ли сериализатор UserBalanceSerializer
        try:
            from .serializers import UserBalanceSerializer
            serializer = UserBalanceSerializer(request.user)
            return Response(serializer.data)
        except ImportError:
            # Альтернатива если сериализатора нет
            return Response({
                'balance': float(request.user.balance),
                'currency': 'RUB',
                'user_id': request.user.id,
                'username': request.user.username
            })
    except Exception as e:
        logger.error(f"Ошибка получения баланса: {e}")
        return Response({
            'error': 'Ошибка получения баланса',
            'balance': 0.0
        }, status=500)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deposit_funds(request):
    """Пополнение баланса пользователя"""
    try:
        from .serializers import DepositSerializer
        serializer = DepositSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        amount = serializer.validated_data['amount']
        
        with db_transaction.atomic():  # Используем переименованное
            user = request.user
            old_balance = user.balance
            user.balance += amount
            user.save()
            
            # ИСПРАВЛЕНИЕ: Убрано поле 'metadata' которое вызывает ошибку
            # Вместо него используем 'payment_data' если поле существует в модели
            # или просто не передаем дополнительные поля
            try:
                # Пробуем создать с payment_data если модель поддерживает
                transaction = Transaction.objects.create(
                    user=user,
                    amount=amount,
                    transaction_type='deposit',
                    status='completed',
                    description=f'Пополнение баланса на {amount} руб.'
                )
            except:
                # Если ошибка, создаем без дополнительных полей
                transaction = Transaction.objects.create(
                    user=user,
                    amount=amount,
                    transaction_type='deposit',
                    status='completed',
                    description=f'Пополнение баланса на {amount} руб.'
                )
            
            # Создаем уведомление
            Notification.objects.create(
                user=user,
                title='Баланс пополнен',
                message=f'Ваш баланс успешно пополнен на {amount} руб. '
                       f'Старый баланс: {old_balance} руб. '
                       f'Новый баланс: {user.balance} руб.',
                notification_type='payment',
                is_read=False
            )
            
            # Логируем в консоль (для теста)
            logger.info(f"\n{'='*50}")
            logger.info(f"ПОПОЛНЕНИЕ БАЛАНСА:")
            logger.info(f"Пользователь: {user.username} (ID: {user.id})")
            logger.info(f"Сумма: {amount} руб.")
            logger.info(f"Старый баланс: {old_balance} руб.")
            logger.info(f"Новый баланс: {user.balance} руб.")
            logger.info(f"{'='*50}")
            
            return Response({
                'success': True,
                'message': f'Баланс успешно пополнен на {amount} руб.',
                'old_balance': float(old_balance),
                'new_balance': float(user.balance),
                'transaction_id': transaction.id
            })
            
    except ImportError:
        # Если сериализатора нет - простая версия
        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Укажите сумму'}, status=400)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Сумма должна быть больше 0'}, status=400)
            
            user = request.user
            old_balance = user.balance
            user.balance += amount
            user.save()
            
            # ИСПРАВЛЕНИЕ: Без metadata
            transaction = Transaction.objects.create(
                user=user,
                amount=amount,
                transaction_type='deposit',
                status='completed',
                description=f'Пополнение баланса на {amount} руб.'
            )
            
            return Response({
                'success': True,
                'message': f'Баланс пополнен на {amount} руб.',
                'old_balance': float(old_balance),
                'new_balance': float(user.balance),
                'transaction_id': transaction.id
            })
            
        except ValueError:
            return Response({'error': 'Неверный формат суммы'}, status=400)
            
    except Exception as e:
        logger.error(f"Ошибка при пополнении баланса: {e}")
        return Response({
            'success': False,
            'error': f'Ошибка при пополнении баланса: {str(e)}'
        }, status=500)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_profile_full(request):
    """Полная информация о профиле пользователя"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

# ========== Просмотр баланса других пользователей (админ) ==========

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_balance_admin(request, user_id):
    """Получить баланс пользователя (для администратора)"""
    # Проверка прав администратора
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return Response(
            {'error': 'Требуются права администратора'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        return Response({
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'balance': float(user.balance),
            'role': user.role,
            'is_active': user.is_active
        })
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=404)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def adjust_balance_admin(request, user_id):
    """Корректировка баланса пользователя администратором"""
    # Проверка прав администратора
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return Response(
            {'error': 'Требуются права администратора'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        amount = request.data.get('amount')
        action = request.data.get('action', 'add')  # 'add' или 'subtract'
        reason = request.data.get('reason', 'Корректировка баланса администратором')
        
        if amount is None:
            return Response({'error': 'Укажите сумму'}, status=400)
        
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return Response({'error': 'Неверный формат суммы'}, status=400)
        
        with db_transaction.atomic():
            old_balance = user.balance
            
            if action == 'add':
                user.balance += amount
                transaction_type = 'deposit'
                description = f'Начисление администратором: {amount} руб. Причина: {reason}'
            elif action == 'subtract':
                if user.balance < amount:
                    return Response(
                        {'error': 'Недостаточно средств на балансе'},
                        status=400
                    )
                user.balance -= amount
                transaction_type = 'payment'
                description = f'Списание администратором: {amount} руб. Причина: {reason}'
            else:
                return Response({'error': 'Неверное действие'}, status=400)
            
            user.save()
            
            # ИСПРАВЛЕНИЕ: Убрано поле metadata из создания транзакции
            try:
                # Пробуем с payment_data
                transaction = Transaction.objects.create(
                    user=user,
                    amount=amount,
                    transaction_type=transaction_type,
                    status='completed',
                    description=description
                )
            except:
                # Без дополнительных полей
                transaction = Transaction.objects.create(
                    user=user,
                    amount=amount,
                    transaction_type=transaction_type,
                    status='completed',
                    description=description
                )
            
            # Создаем уведомление для пользователя
            Notification.objects.create(
                user=user,
                title='Корректировка баланса',
                message=f'Ваш баланс скорректирован администратором. '
                       f'Старый баланс: {old_balance} руб. '
                       f'Новый баланс: {user.balance} руб. '
                       f'Причина: {reason}',
                notification_type='info',
                is_read=False
            )
            
            return Response({
                'success': True,
                'message': f'Баланс пользователя {user.username} изменен',
                'old_balance': float(old_balance),
                'new_balance': float(user.balance),
                'difference': amount if action == 'add' else -amount,
                'action': action,
                'reason': reason,
                'transaction_id': transaction.id
            })
            
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=404)