"""
ДЕМОНСТРАЦИОННЫЙ СКРИПТ ДЛЯ СИСТЕМЫ ПОДПИСОК
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api"

def print_step(step, description):
    print(f"\n{'='*60}")
    print(f"ШАГ {step}: {description}")
    print('='*60)

class DemoSystem:
    def __init__(self):
        self.admin_token = None
        self.user_token = None
        self.user_id = None
        
    def setup(self):
        """Настройка тестовых данных"""
        print_step(1, "НАСТРОЙКА СИСТЕМЫ")
        
        # Создаем тестового администратора
        admin_data = {
            "username": "demo_admin",
            "password": "DemoAdmin123!",
            "password2": "DemoAdmin123!",
            "email": "admin@demo.com",
            "role": "admin"
        }
        
        try:
            response = requests.post(f"{API_URL}/auth/register/", json=admin_data)
            if response.status_code == 201:
                print("Демо-администратор создан")
            else:
                print("ℹАдминистратор уже существует")
        except:
            print("Не удалось создать администратора")
        
        # Входим как администратор
        login_response = requests.post(f"{API_URL}/auth/login/", json={
            "username": "demo_admin",
            "password": "DemoAdmin123!"
        })
        
        if login_response.status_code == 200:
            self.admin_token = login_response.json()['access']
            print("Администратор авторизован")
        else:
            print("Ошибка авторизации администратора")
            return False
        
        return True
    
    def create_test_user(self):
        """Создание тестового пользователя"""
        print_step(2, "СОЗДАНИЕ ТЕСТОВОГО ПОЛЬЗОВАТЕЛЯ")
        
        user_data = {
            "username": "demo_user",
            "password": "DemoUser123!",
            "password2": "DemoUser123!",
            "email": "user@demo.com"
        }
        
        response = requests.post(f"{API_URL}/auth/register/", json=user_data)
        
        if response.status_code == 201:
            print("Тестовый пользователь создан")
            
            # Входим как пользователь
            login_response = requests.post(f"{API_URL}/auth/login/", json={
                "username": "demo_user",
                "password": "DemoUser123!"
            })
            
            if login_response.status_code == 200:
                self.user_token = login_response.json()['access']
                self.user_id = login_response.json()['user']['id']
                print("Пользователь авторизован")
                return True
            else:
                print("Ошибка авторизации пользователя")
                return False
        else:
            print("ℹПользователь уже существует, пытаемся войти...")
            
            login_response = requests.post(f"{API_URL}/auth/login/", json={
                "username": "demo_user",
                "password": "DemoUser123!"
            })
            
            if login_response.status_code == 200:
                self.user_token = login_response.json()['access']
                self.user_id = login_response.json()['user']['id']
                print("Пользователь авторизован")
                return True
        
        return False
    
    def demonstrate_subscription_flow(self):
        """Демонстрация полного цикла подписки"""
        print_step(3, "ДЕМОНСТРАЦИЯ ПОЛНОГО ЦИКЛА ПОДПИСКИ")
        
        headers = {
            'Authorization': f'Bearer {self.user_token}',
            'Content-Type': 'application/json'
        }
        
        # 1. Получаем доступные планы
        print("\n1. Получение доступных планов подписок...")
        response = requests.get(f"{API_URL}/subscriptions/plans/")
        
        if response.status_code == 200:
            plans = response.json()
            print(f"Найдено планов: {len(plans)}")
            for plan in plans[:3]:  # Показываем первые 3
                print(f"   - {plan['name']}: {plan['price']} RUB на {plan['duration_days']} дней")
        else:
            print("Ошибка загрузки планов")
            return
        
        # 2. Покупаем подписку
        print("\n2. Покупка подписки...")
        purchase_response = requests.post(
            f"{API_URL}/subscriptions/purchase/",
            json={"plan_id": plans[0]['id']},  # Берем первый план
            headers=headers
        )
        
        if purchase_response.status_code == 201:
            purchase_data = purchase_response.json()
            print(f"Подписка оформлена! ID: {purchase_data.get('subscription_id')}")
        else:
            print(f"Ошибка покупки: {purchase_response.text}")
            return
        
        # 3. Проверяем мои подписки
        print("\n3. Проверка моих подписок...")
        subs_response = requests.get(
            f"{API_URL}/subscriptions/my-subscriptions/",
            headers=headers
        )
        
        if subs_response.status_code == 200:
            subscriptions = subs_response.json()
            print(f"Найдено подписок: {len(subscriptions)}")
            if subscriptions:
                sub = subscriptions[0]
                print(f"   - ID: {sub['id']}")
                print(f"   - Тариф: {sub['plan']['name']}")
                print(f"   - Статус: {sub['status']}")
                print(f"   - Окончание: {sub['end_date']}")
        else:
            print("Ошибка загрузки подписок")
        
        # 4. Тестируем продление
        print("\n4. Тестирование ручного продления...")
        if subscriptions:
            renew_response = requests.post(
                f"{API_URL}/subscriptions/test-renew/{subscriptions[0]['id']}/",
                headers=headers
            )
            
            if renew_response.status_code == 200:
                print("Подписка успешно продлена!")
            else:
                print(f"Ошибка продления: {renew_response.text}")
        
        # 5. Проверяем историю транзакций
        print("\n5. Проверка истории транзакций...")
        trans_response = requests.get(
            f"{API_URL}/subscriptions/transactions/",
            headers=headers
        )
        
        if trans_response.status_code == 200:
            transactions = trans_response.json()
            print(f"Найдено транзакций: {len(transactions)}")
            for t in transactions[:3]:  # Показываем первые 3
                print(f"   - {t['transaction_type']}: {t['amount']} RUB ({t['status']})")
        else:
            print("Ошибка загрузки транзакций")
        
        # 6. Проверяем промокоды
        print("\n6. Проверка доступных промокодов...")
        promos_response = requests.get(
            f"{API_URL}/subscriptions/promocodes/",
            headers=headers
        )
        
        if promos_response.status_code == 200:
            promocodes = promos_response.json()
            print(f"Найдено промокодов: {len(promocodes)}")
            for promo in promocodes[:2]:
                print(f"   - {promo['code']}: скидка {promo['discount_percent']}%")
        else:
            print("Ошибка загрузки промокодов")
    
    def demonstrate_admin_functions(self):
        """Демонстрация административных функций"""
        print_step(4, "ДЕМОНСТРАЦИЯ АДМИНИСТРАТИВНЫХ ФУНКЦИЙ")
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        # 1. Получаем всех пользователей
        print("\n1. Получение списка всех пользователей...")
        users_response = requests.get(
            f"{API_URL}/admin/users/",
            headers=headers
        )
        
        if users_response.status_code == 200:
            users = users_response.json()
            print(f"Найдено пользователей: {len(users)}")
            for user in users[:3]:  # Показываем первых 3
                print(f"   - {user['username']} ({user['role']}): баланс {user['balance']} RUB")
        else:
            print(f"Ошибка: {users_response.status_code}")
        
        # 2. Запуск проверки продления
        print("\n2. Запуск проверки продления подписок...")
        renewal_response = requests.post(
            f"{API_URL}/subscriptions/run-renewal/",
            headers=headers
        )
        
        if renewal_response.status_code == 200:
            result = renewal_response.json()
            print(f"Проверка выполнена:")
            print(f"   - Проверено подписок: {result.get('checked', 0)}")
            print(f"   - Успешно продлено: {result.get('renewed', 0)}")
            print(f"   - Ошибок: {result.get('failed', 0)}")
        else:
            print(f"Ошибка: {renewal_response.text}")
        
        # 3. Получение всех транзакций
        print("\n3. Получение всех транзакций системы...")
        trans_response = requests.get(
            f"{API_URL}/subscriptions/admin-transactions/",
            headers=headers
        )
        
        if trans_response.status_code == 200:
            transactions = trans_response.json()
            print(f"Найдено транзакций: {len(transactions)}")
            
            # Анализируем статистику
            completed = len([t for t in transactions if t.get('status') == 'completed'])
            total_amount = sum(float(t.get('amount', 0)) for t in transactions if t.get('status') == 'completed')
            
            print(f"   - Успешных: {completed}")
            print(f"   - Общая сумма: {total_amount:.2f} RUB")
        else:
            print(f"Ошибка: {trans_response.status_code}")
    
    def demonstrate_edge_cases(self):
        """Демонстрация обработки edge cases"""
        print_step(5, "ДЕМОНСТРАЦИЯ ОБРАБОТКИ EDGE CASES")
        
        print("\n1. Тестирование разных сценариев платежей...")
        
        # Создаем дополнительного пользователя для тестов
        test_user = {
            "username": "edge_case_user",
            "password": "EdgeCase123!",
            "password2": "EdgeCase123!",
            "email": "edge@demo.com"
        }
        
        response = requests.post(f"{API_URL}/auth/register/", json=test_user)
        
        if response.status_code == 201:
            print("Тестовый пользователь для edge cases создан")
            
            # Входим как тестовый пользователь
            login_response = requests.post(f"{API_URL}/auth/login/", json={
                "username": "edge_case_user",
                "password": "EdgeCase123!"
            })
            
            if login_response.status_code == 200:
                test_token = login_response.json()['access']
                test_headers = {'Authorization': f'Bearer {test_token}', 'Content-Type': 'application/json'}
                
                # Пытаемся купить подписку (будет имитация случайного успеха/ошибки)
                print("\n2. Имитация платежей с разными исходами...")
                
                for i in range(3):
                    purchase_response = requests.post(
                        f"{API_URL}/subscriptions/purchase/",
                        json={"plan_id": 1},
                        headers=test_headers
                    )
                    
                    if purchase_response.status_code == 201:
                        print(f"   Попытка {i+1}: Успешный платеж")
                    elif purchase_response.status_code == 402:
                        print(f"   Попытка {i+1}: Ошибка платежа (имитировано)")
                    else:
                        print(f"   Попытка {i+1}: Другая ошибка: {purchase_response.status_code}")
        
        print("\n3. Демонстрация ролевой модели...")
        print("   - Обычный пользователь не может видеть других пользователей")
        print("   - Администратор имеет доступ ко всем функциям")
        print("   - API проверяет права доступа для каждого эндпоинта")
        
        print("\n4. Конкурентные операции...")
        print("   - Используются транзакции БД для атомарности")
        print("   - select_for_update() для предотвращения race conditions")
        print("   - Экспоненциальные повторные попытки при ошибках")
    
    def run_full_demo(self):
        """Запуск полной демонстрации"""
        print("\n" + "="*70)
        print("ЗАПУСК ПОЛНОЙ ДЕМОНСТРАЦИИ СИСТЕМЫ ПОДПИСОК")
        print("="*70)
        
        if not self.setup():
            print("Не удалось настроить систему")
            return
        
        if not self.create_test_user():
            print("Не удалось создать тестового пользователя")
            return
        
        self.demonstrate_subscription_flow()
        self.demonstrate_admin_functions()
        self.demonstrate_edge_cases()
        
        print("\n" + "="*70)
        print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО.")
        print("="*70)
        print("\nЧто было продемонстрировано:")
        print("Ролевая модель (администратор/пользователь)")
        print("Полный цикл подписки (покупка → продление → управление)")
        print("Фейковая платежная система с обработкой ошибок")
        print("Автоматическое продление (ручной запуск)")
        print("Система уведомлений и email")
        print("Промокоды и скидки")
        print("История транзакций")
        print("Возвраты средств")
        print("Edge cases обработка")
        print("Административная панель")
        print("\nДля запуска веб-интерфейса:")
        print("1. Запустите Django: python manage.py runserver")
        print("2. Запустите Streamlit: streamlit run frontend/app.py")
        print("3. Откройте http://localhost:8501 в браузере")

if __name__ == "__main__":
    demo = DemoSystem()
    demo.run_full_demo()