import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

API_BASE_URL = "http://127.0.0.1:8000/api"

def is_admin_user():
    if 'user' not in st.session_state:
        return False
    
    user = st.session_state['user']
    return user.get('role') == 'admin' or user.get('is_staff') == True or user.get('is_superuser') == True

def get_auth_headers():
    if 'access_token' not in st.session_state:
        return None
    return {
        'Authorization': f'Bearer {st.session_state["access_token"]}',
        'Content-Type': 'application/json'
    }

def format_balance(balance):
    """Форматирует баланс, преобразуя строку в число если нужно"""
    if balance is None:
        return "0.00 RUB"
    
    try:
        # Если это строка, преобразуем в число
        if isinstance(balance, str):
            balance = float(balance)
        return f"{balance:.2f} RUB"
    except (ValueError, TypeError):
        return f"{balance} RUB"

def fetch_all_users(headers):
    try:
        response = requests.get(f"{API_BASE_URL}/admin/users/", headers=headers, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            st.error("У вас нет прав для просмотра пользователей")
            return []
        else:
            st.warning(f"API вернул код {response.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        st.error("Не удалось подключиться к серверу")
        return []
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return []

def fetch_all_subscriptions(headers):
    try:
        response = requests.get(f"{API_BASE_URL}/subscriptions/admin-subscriptions/", headers=headers, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            return []
        else:
            return []
    except:
        return []

def fetch_all_transactions(headers):
    try:
        response = requests.get(f"{API_BASE_URL}/subscriptions/admin-transactions/", headers=headers, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except:
        return []

def format_date(date_string):
    if not date_string:
        return ""
    try:
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_string[:10]

def main():
    st.set_page_config(
        page_title="Админ-панель",
        page_icon="",
        layout="wide"
    )
    
    if 'access_token' not in st.session_state:
        st.error("Вы не авторизованы")
        if st.button("Войти в систему"):
            st.switch_page("pages/01_auth.py")
        return
    
    if not is_admin_user():
        st.error("Доступ запрещен")
        st.warning("Требуются права администратора для доступа к этой странице.")
        
        user = st.session_state.get('user', {})
        st.info(f"Вы вошли как: {user.get('username')} (роль: {user.get('role', 'user')})")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Выйти"):
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
    
    st.header("Быстрые действия")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Проверить продления", help="Запустить проверку подписок для продления", use_container_width=True):
            try:
                with st.spinner("Проверяем..."):
                    response = requests.post(
                        f"{API_BASE_URL}/subscriptions/run-renewal/",
                        headers=headers,
                        timeout=30
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"Проверено: {result.get('checked', 0)} подписок")
                        st.success(f"Продлено: {result.get('renewed', 0)}")
                        if result.get('failed', 0) > 0:
                            st.warning(f"Ошибок: {result.get('failed', 0)}")
                        
                        if result.get('results'):
                            with st.expander("Детали результатов"):
                                for res in result['results']:
                                    if res.get('status') == 'renewed':
                                        st.info(f"Подписка {res.get('subscription_id')} продлена для {res.get('user')}")
                                    elif res.get('status') == 'failed':
                                        st.error(f"Ошибка подписки {res.get('subscription_id')}: {res.get('error')}")
                    elif response.status_code == 403:
                        st.error("У вас нет прав для этого действия")
                    else:
                        st.error(f"Ошибка API: {response.status_code}")
                        st.text(response.text)
            except requests.exceptions.Timeout:
                st.error("Таймаут запроса")
            except Exception as e:
                st.error(f"Ошибка: {e}")
    
    with col2:
        email = st.text_input("Email для теста", value=st.session_state['user'].get('email', ''), key="email_input")
        if st.button("Отправить тест email", help="Отправить тестовое email уведомление", use_container_width=True):
            try:
                with st.spinner("Отправляем..."):
                    response = requests.post(
                        f"{API_BASE_URL}/subscriptions/send-test-email/",
                        json={"email": email},
                        headers=headers
                    )
                    if response.status_code == 200:
                        st.success("Тестовый email отправлен!")
                        st.info("Проверьте консоль Django для просмотра email")
                    else:
                        st.error(f"Ошибка: {response.json().get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Ошибка: {e}")
    
    with col3:
        if st.button("Обновить статистику", use_container_width=True):
            st.rerun()
    
    with col4:
        if st.button("Создать тестовые данные", use_container_width=True):
            try:
                with st.spinner("Создаем..."):
                    response = requests.post(
                        f"{API_BASE_URL}/subscriptions/purchase/",
                        json={"plan_id": 1},
                        headers=headers
                    )
                    if response.status_code == 201:
                        st.success("Тестовая подписка создана!")
                    else:
                        st.warning(f"Не удалось создать подписку: {response.status_code}")
            except Exception as e:
                st.error(f"Ошибка: {e}")
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Дашборд",
        "Пользователи",
        "Подписки", 
        "Транзакции",
        "Настройки"
    ])
    
    with tab1:
        st.header("Дашборд системы")
        
        with st.spinner("Загружаем статистику..."):
            users = fetch_all_users(headers)
            subscriptions = fetch_all_subscriptions(headers)
            transactions = fetch_all_transactions(headers)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Всего пользователей", len(users) if users else "N/A")
        with col2:
            active_subs = len([s for s in subscriptions if s.get('status') == 'active']) if subscriptions else 0
            st.metric("Активных подписок", active_subs)
        with col3:
            if transactions:
                total_amount = 0
                for t in transactions:
                    if t.get('status') == 'completed':
                        try:
                            amount = t.get('amount', 0)
                            if isinstance(amount, str):
                                amount = float(amount)
                            total_amount += amount
                        except:
                            pass
                st.metric("Выручка", f"{total_amount:.0f} RUB")
            else:
                st.metric("Выручка", "N/A")
        with col4:
            if users and subscriptions:
                conversion = (len(subscriptions) / len(users)) * 100 if users else 0
                st.metric("Конверсия", f"{conversion:.1f}%")
            else:
                st.metric("Конверсия", "N/A")
        
        st.subheader("Последние события")
        if transactions:
            for t in transactions[:5]:
                if isinstance(t, dict):
                    user_data = t.get('user', {})
                    if isinstance(user_data, dict):
                        username = user_data.get('username', 'Unknown')
                    else:
                        username = str(user_data)
                    
                    status_text = "Успешно" if t.get('status') == 'completed' else "Ошибка"
                    st.write(f"{status_text} - {username} - {t.get('transaction_type')} - {t.get('amount')} RUB")
                else:
                    st.write(f"Неизвестный формат транзакции: {type(t)}")
        else:
            st.info("Нет данных о транзакциях")
    
    with tab2:
        st.header("Управление пользователями")
        
        users = fetch_all_users(headers)
        
        if users:
            col1, col2 = st.columns(2)
            with col1:
                search = st.text_input("Поиск пользователей", placeholder="Имя, email...", key="user_search")
            with col2:
                role_filter = st.selectbox("Фильтр по роли", ["Все", "user", "admin"], key="role_filter")
            
            filtered_users = users
            if search:
                filtered_users = [u for u in filtered_users if search.lower() in u.get('username', '').lower() or search.lower() in u.get('email', '').lower()]
            if role_filter != "Все":
                filtered_users = [u for u in filtered_users if u.get('role') == role_filter]
            
            df_data = []
            for user in filtered_users:
                df_data.append({
                    'ID': user.get('id'),
                    'Имя': user.get('username'),
                    'Email': user.get('email'),
                    'Роль': user.get('role', 'user'),
                    'Баланс': format_balance(user.get('balance', 0)),
                    'Активен': 'Да' if user.get('is_active') else 'Нет',
                    'Дата регистрации': format_date(user.get('date_joined'))
                })
            
            if df_data:
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.subheader("Управление пользователем")
                selected_username = st.selectbox("Выберите пользователя", df['Имя'].tolist(), key="user_select")
                
                if selected_username:
                    selected_user = next((u for u in users if u['username'] == selected_username), None)
                    
                    if selected_user:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write("Текущая роль:", selected_user.get('role', 'user'))
                            new_role = st.selectbox("Новая роль", ["user", "admin"], key="new_role_select")
                            if st.button("Изменить роль", key="change_role_btn"):
                                st.info(f"Функция изменения роли будет реализована в API")
                        
                        with col2:
                            balance = selected_user.get('balance', 0)
                            st.write("Баланс:", format_balance(balance))
                            try:
                                if isinstance(balance, str):
                                    balance = float(balance)
                            except:
                                balance = 0
                            new_balance = st.number_input("Новый баланс", value=float(balance), key="new_balance")
                            if st.button("Изменить баланс", key="change_balance_btn"):
                                st.info(f"Функция изменения баланса будет реализована в API")
                        
                        with col3:
                            if st.button("Отправить приветствие", key="welcome_btn"):
                                st.success(f"Приветствие отправлено пользователю {selected_username}")
            else:
                st.info("Пользователи не найдены")
        else:
            st.warning("Не удалось загрузить пользователей")
            st.info("Убедитесь, что API endpoint /api/admin/users/ доступен")
    
    with tab3:
        st.header("Управление подписками")
        
        subscriptions = fetch_all_subscriptions(headers)
        
        if subscriptions:
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox("Статус", ["Все", "active", "expired", "canceled", "pending"], key="status_filter")
            with col2:
                search_user = st.text_input("Поиск по пользователю", placeholder="Имя пользователя...", key="user_filter")
            with col3:
                show_expiring = st.checkbox("Показывать истекающие (≤7 дней)", key="expiring_check")
            
            filtered_subs = subscriptions
            if status_filter != "Все":
                filtered_subs = [s for s in filtered_subs if s.get('status') == status_filter]
            if search_user:
                filtered_subs = [s for s in filtered_subs if search_user.lower() in s.get('user', {}).get('username', '').lower()]
            if show_expiring:
                filtered_subs = [s for s in filtered_subs if s.get('status') == 'active']
            
            if filtered_subs:
                df_data = []
                for sub in filtered_subs[:50]:
                    plan_price = sub.get('plan', {}).get('price', 0)
                    try:
                        if isinstance(plan_price, str):
                            plan_price = float(plan_price)
                    except:
                        plan_price = 0
                    
                    df_data.append({
                        'ID': sub.get('id'),
                        'Пользователь': sub.get('user', {}).get('username', 'Unknown'),
                        'Тариф': sub.get('plan', {}).get('name', 'Unknown'),
                        'Статус': sub.get('status'),
                        'Начало': format_date(sub.get('start_date')),
                        'Окончание': format_date(sub.get('end_date')),
                        'Цена': f"{plan_price:.2f} RUB",
                        'Автопродление': 'Да' if sub.get('auto_renew') else 'Нет'
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.subheader("Ручное управление")
                selected_id = st.number_input("ID подписки для управления", min_value=1, value=1, key="sub_id_input")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Продлить подписку", key="renew_btn"):
                        try:
                            response = requests.post(
                                f"{API_BASE_URL}/subscriptions/test-renew/{selected_id}/",
                                headers=headers
                            )
                            if response.status_code == 200:
                                st.success("Подписка продлена!")
                                st.rerun()
                            else:
                                st.error(f"Ошибка: {response.text}")
                        except Exception as e:
                            st.error(f"Ошибка: {e}")
                
                with col2:
                    if st.button("Отменить подписку", key="cancel_btn"):
                        st.info("Функция отмены будет реализована")
                
                with col3:
                    if st.button("Изменить тариф", key="change_plan_btn"):
                        st.info("Функция смены тарифа будет реализована")
            else:
                st.info("Подписки не найдены по выбранным фильтрами")
        else:
            st.warning("Не удалось загрузить подписки")
    
    with tab4:
        st.header("История транзакций")
        
        transactions = fetch_all_transactions(headers)
        
        if transactions:
            col1, col2, col3 = st.columns(3)
            
            completed = len([t for t in transactions if t.get('status') == 'completed'])
            failed = len([t for t in transactions if t.get('status') == 'failed'])
            
            total_amount = 0
            for t in transactions:
                if t.get('status') == 'completed':
                    try:
                        amount = t.get('amount', 0)
                        if isinstance(amount, str):
                            amount = float(amount)
                        total_amount += amount
                    except:
                        pass
            
            col1.metric("Всего транзакций", len(transactions))
            col2.metric("Успешных", completed)
            col3.metric("Общая сумма", f"{total_amount:.2f} RUB")
            
            col1, col2 = st.columns(2)
            with col1:
                type_filter = st.selectbox("Тип транзакции", ["Все", "purchase", "renewal", "refund"], key="type_filter")
            with col2:
                status_filter = st.selectbox("Статус", ["Все", "completed", "failed", "pending"], key="status_filter_tx")
            
            filtered_trans = transactions
            if type_filter != "Все":
                filtered_trans = [t for t in filtered_trans if t.get('transaction_type') == type_filter]
            if status_filter != "Все":
                filtered_trans = [t for t in filtered_trans if t.get('status') == status_filter]
            
            if filtered_trans:
                df_data = []
                for t in filtered_trans[:100]:
                    user_data = t.get('user', {})
                    if isinstance(user_data, dict):
                        username = user_data.get('username', 'Unknown')
                    else:
                        username = str(user_data)
                    
                    amount = t.get('amount', 0)
                    try:
                        if isinstance(amount, str):
                            amount = float(amount)
                    except:
                        pass
                    
                    df_data.append({
                        'ID': t.get('id'),
                        'Пользователь': username,
                        'Тип': t.get('transaction_type'),
                        'Сумма': f"{amount:.2f} RUB",
                        'Статус': t.get('status'),
                        'Дата': format_date(t.get('created_at')),
                        'Описание': t.get('description', '')[:50] + ('...' if len(t.get('description', '')) > 50 else '')
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                if st.button("Экспорт в CSV", key="export_csv"):
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Скачать CSV",
                        data=csv,
                        file_name=f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_csv"
                    )
            else:
                st.info("Транзакции не найдены по выбранным фильтрам")
        else:
            st.warning("Не удалось загрузить транзакции")
    
    with tab5:
        st.header("Настройки системы")
        
        st.subheader("Настройки уведомлений")
        
        col1, col2 = st.columns(2)
        with col1:
            email_enabled = st.checkbox("Включить email уведомления", value=True, key="email_enabled")
            renewal_notifications = st.checkbox("Уведомления о продлении", value=True, key="renewal_notify")
        with col2:
            expiration_notifications = st.checkbox("Уведомления об истечении", value=True, key="expire_notify")
            payment_failed_notifications = st.checkbox("Уведомления об ошибках платежей", value=True, key="payment_notify")
        
        st.subheader("Настройки продления")
        renewal_hour = st.slider("Время ежедневной проверки (час)", 0, 23, 0, key="renewal_hour")
        days_before_notify = st.slider("Дней до уведомления об истечении", 1, 7, 3, key="days_notify")
        
        st.subheader("Настройки возвратов")
        refund_enabled = st.checkbox("Разрешить возвраты", value=True, key="refund_enabled")
        refund_days = st.slider("Дней для возврата", 1, 30, 7, key="refund_days")
        
        if st.button("Сохранить настройки", type="primary", key="save_settings"):
            st.success("Настройки сохранены (в демо-режиме)")
        
        st.markdown("---")
        st.subheader("Технические настройки")
        
        if st.button("Очистить кэш", key="clear_cache"):
            st.info("Кэш очищен")
        
        if st.button("Перезапустить фоновые задачи", key="restart_tasks"):
            st.info("Фоновые задачи перезапущены")
    
    with st.sidebar:
        st.markdown("### Информация")
        user = st.session_state.get('user', {})
        st.info(f"Имя: {user.get('username')}")
        st.info(f"Роль: {user.get('role', 'user')}")
        st.info(f"Email: {user.get('email', 'Не указан')}")
        
        st.markdown("---")
        st.markdown("### Статус системы")
        
        try:
            response = requests.get(f"{API_BASE_URL}/subscriptions/plans/", timeout=2)
            if response.status_code == 200:
                st.success("API работает")
            else:
                st.error(f"API: {response.status_code}")
        except:
            st.error("API недоступен")
        
        try:
            response = requests.get(f"{API_BASE_URL}/subscriptions/plans/", timeout=2)
            if response.status_code == 200:
                data = response.json()
                st.success(f"БД: {len(data)} планов")
        except:
            st.error("Ошибка БД")
        
        st.info("Фоновые задачи: Не активны")
        
        st.markdown("---")
        if st.button("Обновить все"):
            st.rerun()
        
        if st.button("Выйти"):
            for key in ['access_token', 'refresh_token', 'user']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()