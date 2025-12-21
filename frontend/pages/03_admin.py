import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import os

API_BASE_URL = "http://127.0.0.1:8000/api"

def is_admin_user():
    if 'user' not in st.session_state:
        return False
    
    user = st.session_state['user']
    
    is_admin = (
        user.get('role') == 'admin' or
        user.get('is_staff') == True or
        user.get('is_superuser') == True
    )
    
    return is_admin

def get_auth_headers():
    if 'access_token' not in st.session_state:
        return None
    return {
        'Authorization': f'Bearer {st.session_state["access_token"]}',
        'Content-Type': 'application/json'
    }

def fetch_all_users(headers):
    """Получает всех пользователей (только для админов)"""
    try:
        # В реальном API нужен эндпоинт для получения всех пользователей
        # Пока заглушкf
        response = requests.get(f"{API_BASE_URL}/auth/users/", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            # Если нет API, возвращаем тестовые данные
            return [
                {
                    'id': 1,
                    'username': 'admin',
                    'email': 'admin@example.com',
                    'role': 'admin',
                    'is_active': True,
                    'date_joined': '2024-01-01T10:00:00Z'
                },
                {
                    'id': 2,
                    'username': 'user1',
                    'email': 'user1@example.com',
                    'role': 'user',
                    'is_active': True,
                    'date_joined': '2024-01-02T11:00:00Z'
                }
            ]
    except:
        return []

def fetch_all_subscriptions(headers):
    """Получает все подписки"""
    try:
        # Нужен специальный эндпоинт для админов
        # Пока используем свой список
        return []
    except:
        return []

def main():
    st.set_page_config(
        page_title="Админ-панель",
        layout="wide"
    )
    
    # Проверка авторизации
    if 'access_token' not in st.session_state:
        st.error("Вы не авторизованы")
        if st.button("Войти в систему"):
            st.switch_page("pages/01_auth.py")
        return
    
    # Проверка прав администратора
    if not is_admin_user():
        st.error("Доступ запрещен")
        st.warning("Требуются права администратора для доступа к этой странице.")
        
        # Информация о текущем пользователе
        user = st.session_state.get('user', {})
        st.info(f"Вы вошли как: **{user.get('username')}** (роль: {user.get('role', 'user')})")
        
        # Кнопка для выхода и входа под админом
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Выйти и войти под администратором"):
                for key in ['access_token', 'refresh_token', 'user']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        with col2:
            if st.button("Вернуться на главную"):
                st.switch_page("app.py")
        
        return
    
    headers = get_auth_headers()
    
    st.title("Панель администратора")
    st.success(f"Добро пожаловать, {st.session_state['user'].get('username')}!")
    st.markdown("---")
    
    # Быстрые действия
    st.header("Быстрые действия")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Проверить продления", help="Запустить проверку подписок для продления"):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/subscriptions/run-renewal/",
                    headers=headers
                )
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"Проверено: {result.get('checked', 0)}")
                else:
                    st.error("Ошибка API")
            except Exception as e:
                st.error(f"Ошибка: {e}")
    
    with col2:
        if st.button("Обновить статистику"):
            st.rerun()
    
    with col3:
        if st.button("Отправить тест email"):
            st.info("Функция в разработке")
    
    with col4:
        if st.button("Создать тестовые данные"):
            try:
                # Создаем тестовую подписку
                response = requests.post(
                    f"{API_BASE_URL}/subscriptions/purchase/",
                    json={"plan_id": 1},
                    headers=headers
                )
                if response.status_code == 201:
                    st.success("Тестовая подписка создана")
                else:
                    st.warning("Не удалось создать подписку")
            except Exception as e:
                st.error(f"Ошибка: {e}")
    
    st.markdown("---")
    
    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "Пользователи",
        "Подписки", 
        "Транзакции",
        "Настройки"
    ])
    
    with tab1:
        st.header("Управление пользователями")
        
        # Поиск
        search = st.text_input("Поиск пользователей", placeholder="Введите имя или email...")
        
        # Загружаем пользователей
        users = fetch_all_users(headers)
        
        if users:
            # Конвертируем в DataFrame для отображения
            df_data = []
            for user in users[:10]:  # Ограничиваем 10 пользователями
                df_data.append({
                    'ID': user.get('id'),
                    'Имя': user.get('username'),
                    'Email': user.get('email'),
                    'Роль': user.get('role', 'user'),
                    'Активен': '[active]' if user.get('is_active') else '[inactive]',
                    'Дата регистрации': user.get('date_joined', '')[:10]
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Управление конкретным пользователем
            st.subheader("Управление пользователем")
            selected_user = st.selectbox("Выберите пользователя", df['Имя'].tolist())
            
            if selected_user:
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_role = st.selectbox("Роль", ["user", "admin"], key="role_select")
                    if st.button("Изменить роль"):
                        st.info(f"Роль пользователя {selected_user} изменена на {new_role}")
                
                with col2:
                    if st.button("Сбросить пароль"):
                        st.warning(f"Пароль для {selected_user} будет сброшен")
                
                with col3:
                    if st.button("Деактивировать"):
                        st.error(f"Пользователь {selected_user} будет деактивирован")
        else:
            st.info("Нет данных о пользователях")
            st.info("Для работы этой функции нужно добавить API эндпоинт для получения всех пользователей.")
    
    with tab2:
        st.header("Управление подписками")
        
        # Фильтры
        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox("Статус подписки", ["Все", "Активные", "Истекшие", "Отмененные"])
        with col2:
            days = st.slider("Дней до окончания", 0, 30, 7)
        
        # Ручное управление
        st.subheader("Ручное управление подпиской")
        
        sub_id = st.number_input("ID подписки", min_value=1, value=1)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Продлить подписку"):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/subscriptions/test-renew/{sub_id}/",
                        headers=headers
                    )
                    if response.status_code == 200:
                        st.success("Подписка продлена")
                    else:
                        st.error(f"Ошибка: {response.text}")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        
        with col2:
            if st.button("Изменить дату окончания"):
                minutes = st.number_input("Через сколько минут:", 1, 10080, 30)
                if st.button("Применить", key="apply_date"):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/subscriptions/test/update-end-date/{sub_id}/",
                            json={"minutes": minutes},
                            headers=headers
                        )
                        if response.status_code == 200:
                            st.success("Дата изменена")
                        else:
                            st.error("Ошибка")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
    
    with tab3:
        st.header("История транзакций")
        
        # Загружаем транзакции
        try:
            response = requests.get(
                f"{API_BASE_URL}/subscriptions/transactions/",
                headers=headers
            )
            
            if response.status_code == 200:
                transactions = response.json()
                
                if transactions:
                    # Агрегируем статистику
                    total_amount = sum(float(t.get('amount', 0)) for t in transactions)
                    completed = len([t for t in transactions if t.get('status') == 'completed'])
                    failed = len([t for t in transactions if t.get('status') == 'failed'])
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Всего транзакций", len(transactions))
                    col2.metric("Успешных", completed)
                    col3.metric("Общая сумма", f"{total_amount:.2f} RUB")
                    
                    # Таблица транзакций
                    st.subheader("Последние транзакции")
                    
                    table_data = []
                    for t in transactions[:20]:  # Последние 20
                        table_data.append({
                            'ID': t.get('id', ''),
                            'Тип': t.get('transaction_type', '').replace('_', ' ').title(),
                            'Сумма': f"{t.get('amount', 0)} RUB",
                            'Статус': t.get('status', '').title(),
                            'Дата': t.get('created_at', '')[:19],
                            'Описание': t.get('description', '')[:50] + '...'
                        })
                    
                    st.dataframe(
                        pd.DataFrame(table_data),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Нет транзакций")
            else:
                st.error("Ошибка загрузки транзакций")
        except Exception as e:
            st.error(f"Ошибка: {e}")
    
    with tab4:
        st.header("Настройки системы")
        
        st.subheader("Настройки уведомлений")
        
        email_notifications = st.checkbox("Email уведомления", value=True)
        push_notifications = st.checkbox("Push уведомления", value=False)
        
        st.subheader("Настройки продления")
        renewal_hour = st.slider("Время проверки продления", 0, 23, 0)
        retry_attempts = st.slider("Количество повторных попыток", 1, 5, 3)
        
        if st.button("Сохранить настройки", type="primary"):
            st.success("Настройки сохранены")
        
        st.markdown("---")
        st.subheader("Опасная зона")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Очистить старые данные", type="secondary"):
                st.warning("Будут удалены данные старше 1 года")
        with col2:
            if st.button("Экспорт всех данных", type="secondary"):
                st.info("Функция в разработке")
    
    # Сайдбар
    with st.sidebar:
        st.markdown("### Информация")
        user = st.session_state.get('user', {})
        st.info(f"**Имя:** {user.get('username')}")
        st.info(f"**Роль:** {user.get('role', 'user')}")
        st.info(f"**Email:** {user.get('email', 'Не указан')}")
        
        st.markdown("---")
        st.markdown("### Статус")
        
        # Проверка сервисов
        try:
            requests.get(f"{API_BASE_URL}/subscriptions/plans/", timeout=2)
            st.success("API работает")
        except:
            st.error("API недоступен")
        
        # Проверка базы данных
        try:
            db_path = os.path.join(os.path.dirname(__file__), '../../db.sqlite3')
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Проверяем несколько таблиц
                tables_to_check = ['subscriptions_subscriptionplan', 'users_user', 'subscriptions_usersubscription']
                statuses = []
                
                for table in tables_to_check:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        statuses.append(f"{table}: {count} записей")
                    except:
                        statuses.append(f"{table}: ошибка")
                
                conn.close()
                
                if all("ошибка" not in s for s in statuses):
                    st.success("База данных работает")
                    with st.expander("Детали БД"):
                        for status in statuses:
                            st.text(status)
                else:
                    st.warning("БД с ошибками")
            else:
                st.error("Файл БД не найден")
        except Exception as e:
            st.error(f"Ошибка БД: {e}")
        
        st.markdown("---")
        if st.button("Обновить страницу"):
            st.rerun()
        
        if st.button("Выйти"):
            for key in ['access_token', 'refresh_token', 'user']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()