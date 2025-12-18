import time
import random
from datetime import datetime
from django.conf import settings

class FakePaymentGateway:
    
    @staticmethod
    def process_payment(amount, user_id, description=""):
        """
        Обрабатывает платеж
        Возвращает dict с результатом
        """
        # Имитация задержки сети
        time.sleep(random.uniform(0.5, 2.0))
        
        # Вероятность успешного платежа 90%
        if random.random() < 0.9:
            # Успешный платеж
            transaction_id = f"FPG_{int(time.time())}_{random.randint(1000, 9999)}"
            return {
                'success': True,
                'transaction_id': transaction_id,
                'amount': amount,
                'status': 'completed',
                'message': 'Платеж успешно обработан',
                'timestamp': datetime.now().isoformat(),
                'gateway_data': {
                    'fake_gateway': True,
                    'approval_code': f"APPROVAL_{random.randint(100000, 999999)}"
                }
            }
        else:
            # Неуспешный платеж
            error_reasons = [
                'Недостаточно средств',
                'Сеть недоступна',
                'Таймаут соединения',
                'Неверные данные карты',
                'Превышен лимит'
            ]
            return {
                'success': False,
                'transaction_id': None,
                'amount': amount,
                'status': 'failed',
                'message': random.choice(error_reasons),
                'timestamp': datetime.now().isoformat(),
                'gateway_data': {
                    'fake_gateway': True,
                    'error_code': f"ERR_{random.randint(100, 999)}"
                }
            }
    
    @staticmethod
    def refund_payment(original_transaction_id, amount):
        """
        Возврат средств
        """
        time.sleep(random.uniform(0.5, 1.5))
        
        if random.random() < 0.95:
            return {
                'success': True,
                'refund_id': f"REFUND_{int(time.time())}_{random.randint(1000, 9999)}",
                'amount': amount,
                'status': 'refunded',
                'message': 'Возврат успешно обработан',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'refund_id': None,
                'amount': amount,
                'status': 'failed',
                'message': 'Ошибка возврата',
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def check_balance(user_id):
        """
        Проверяет баланс в платежной системе
        """
        time.sleep(0.3)
        # Генерируем случайный баланс для тестирования
        balance = random.uniform(1000, 10000)
        return {
            'success': True,
            'balance': round(balance, 2),
            'currency': 'RUB',
            'timestamp': datetime.now().isoformat()
        }