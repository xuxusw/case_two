import streamlit as st
import requests
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000/api"

def get_auth_headers():
    if 'access_token' not in st.session_state:
        return None
    return {
        'Authorization': f'Bearer {st.session_state["access_token"]}',
        'Content-Type': 'application/json'
    }

def main():
    st.set_page_config(
        page_title="Мой баланс",
        page_icon="",
        layout="wide"
    )
    
    if 'access_token' not in st.session_state:
        st.error("Вы не авторизованы")
        if st.button("Войти в систему"):
            st.switch_page("pages/01_auth.py")
        return
    
    headers = get_auth_headers()
    
    st.title("Мой баланс")
    st.markdown("---")
    
    try:
        # Получаем текущий баланс (ИСПРАВЛЕННЫЙ ПУТЬ)
        balance_response = requests.get(
            f"{API_BASE_URL}/auth/balance/",
            headers=headers
        )
        
        if balance_response.status_code == 200:
            balance_data = balance_response.json()
            current_balance = float(balance_data.get('balance', 0))
            
            # Отображаем текущий баланс
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Текущий баланс",
                    f"{current_balance:.2f} руб.",
                    help="Доступная сумма для оплаты подписок"
                )
            
            # Получаем информацию о пользователе (ИСПРАВЛЕННЫЙ ПУТЬ)
            profile_response = requests.get(
                f"{API_BASE_URL}/auth/profile/full/",
                headers=headers
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                with col2:
                    st.metric(
                        "Количество подписок",
                        f"{len(profile_data.get('subscriptions', []))}",
                        help="Активные подписки"
                    )
                
                with col3:
                    role_display = "Администратор" if profile_data.get('role') == 'admin' else "Пользователь"
                    st.metric(
                        "Статус",
                        role_display,
                        help="Роль в системе"
                    )
            
            st.markdown("---")
            
            # Раздел пополнения баланса
            st.subheader("Пополнить баланс")
            
            with st.form("deposit_form"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    amount = st.number_input(
                        "Сумма пополнения (руб.)",
                        min_value=0.0,
                        max_value=50000.0,
                        value=1000.0,
                        step=100.0,
                        format="%.2f"
                    )
                    
                    deposit_method = st.selectbox(
                        "Способ оплаты",
                        ["Банковская карта", "Электронный кошелек", "Банковский перевод"]
                    )
                
                with col2:
                    st.write("")
                    st.write("")
                    submit_button = st.form_submit_button(
                        "Пополнить баланс",
                        type="primary",
                        use_container_width=True
                    )
                
                if submit_button:
                    if amount < 0:
                        st.error("Сумма не может быть отрицательной")
                    elif amount == 0:
                        st.warning("Введите сумму больше 0")
                    else:
                        with st.spinner("Обработка платежа..."):
                            # ИСПРАВЛЕННЫЙ ПУТЬ: /auth/deposit/ вместо /users/deposit/
                            deposit_response = requests.post(
                                f"{API_BASE_URL}/auth/deposit/",
                                headers=headers,
                                json={"amount": float(amount)}
                            )
                            
                            if deposit_response.status_code == 200:
                                deposit_data = deposit_response.json()
                                st.success(f"Баланс успешно пополнен на {amount:.2f} руб.!")
                                
                                # Показываем результат
                                col_success1, col_success2 = st.columns(2)
                                with col_success1:
                                    st.info(f"Новый баланс: **{deposit_data.get('new_balance')} руб.**")
                                with col_success2:
                                    st.info(f"ID транзакции: `{deposit_data.get('transaction_id')}`")
                                
                                # Обновляем страницу
                                st.rerun()
                            else:
                                try:
                                    error_data = deposit_response.json()
                                    error_msg = error_data.get('error', 'Неизвестная ошибка')
                                except:
                                    error_msg = f"HTTP {deposit_response.status_code}"
                                st.error(f"Ошибка: {error_msg}")
            
            st.markdown("---")
            
            # Раздел управления автопродлением
            st.subheader("Управление автопродлением")
            
            # Получаем подписки пользователя
            subscriptions_response = requests.get(
                f"{API_BASE_URL}/subscriptions/my-subscriptions/",
                headers=headers
            )
            
            if subscriptions_response.status_code == 200:
                subscriptions = subscriptions_response.json()
                
                active_subscriptions = [s for s in subscriptions if s.get('status') == 'active']
                
                if active_subscriptions:
                    st.write("Ваши активные подписки:")
                    
                    for subscription in active_subscriptions:
                        with st.container():
                            cols = st.columns([3, 2, 2, 1])
                            
                            with cols[0]:
                                st.write(f"**{subscription.get('plan_name')}**")
                                if subscription.get('end_date'):
                                    try:
                                        end_date = datetime.fromisoformat(
                                            subscription.get('end_date').replace('Z', '+00:00')
                                        )
                                        st.caption(f"Действует до: {end_date.strftime('%d.%m.%Y')}")
                                    except:
                                        st.caption(f"Действует до: {subscription.get('end_date')}")
                            
                            with cols[1]:
                                st.write(f"Цена: {subscription.get('plan_price')} руб.")
                            
                            with cols[2]:
                                auto_renew = subscription.get('auto_renew', False)
                                status_color = "#4CAF50" if auto_renew else "#F44336"
                                status_text = "Включено" if auto_renew else "Выключено"
                                st.markdown(f"Автопродление: <span style='color:{status_color}'>{status_text}</span>", 
                                          unsafe_allow_html=True)
                            
                            with cols[3]:
                                # ИСПРАВЛЕННЫЙ URL для переключения автопродления
                                if auto_renew:
                                    if st.button("Выключить", key=f"off_{subscription.get('id')}", type="secondary"):
                                        try:
                                            # ИСПРАВЛЕНО: добавлен префикс 'my-subscriptions'
                                            response = requests.patch(
                                                f"{API_BASE_URL}/subscriptions/my-subscriptions/{subscription.get('id')}/toggle-auto-renew/",
                                                headers=headers,
                                                json={"auto_renew": False}
                                            )
                                            if response.status_code == 200:
                                                st.success("Автопродление отключено")
                                                st.rerun()
                                            else:
                                                error_data = response.json()
                                                st.error(f"Ошибка: {error_data.get('error', 'Неизвестная ошибка')}")
                                        except Exception as e:
                                            st.error(f"Ошибка соединения: {str(e)}")
                                else:
                                    if st.button("Включить", key=f"on_{subscription.get('id')}", type="primary"):
                                        try:
                                            # ИСПРАВЛЕНО: добавлен префикс 'my-subscriptions'
                                            response = requests.patch(
                                                f"{API_BASE_URL}/subscriptions/my-subscriptions/{subscription.get('id')}/toggle-auto-renew/",
                                                headers=headers,
                                                json={"auto_renew": True}
                                            )
                                            if response.status_code == 200:
                                                st.success("Автопродление включено")
                                                st.rerun()
                                            else:
                                                error_data = response.json()
                                                st.error(f"Ошибка: {error_data.get('error', 'Неизвестная ошибка')}")
                                        except Exception as e:
                                            st.error(f"Ошибка соединения: {str(e)}")
                            
                            st.divider()
                    
                    st.info("Автопродление автоматически списывает средства с баланса "
                            "за 24 часа до окончания подписки.")
                else:
                    st.info("У вас нет активных подписок для управления автопродлением.")
            else:
                st.error("Ошибка загрузки подписок")
            
            st.markdown("---")
            
            # История транзакций
            st.subheader("История операций")
            
            # Получаем транзакции
            transactions_response = requests.get(
                f"{API_BASE_URL}/subscriptions/transactions/",
                headers=headers
            )
            
            if transactions_response.status_code == 200:
                transactions = transactions_response.json()
                
                if transactions:
                    # Фильтры
                    col_filter1, col_filter2 = st.columns(2)
                    with col_filter1:
                        transaction_type = st.selectbox(
                            "Тип операции",
                            ["Все", "deposit", "subscription_purchase", "subscription_renewal", "refund", "subscription_auto_renewal"],
                            key="transaction_type_filter"
                        )
                    
                    # Применяем фильтры
                    filtered_transactions = transactions
                    if transaction_type != "Все":
                        filtered_transactions = [t for t in transactions if t.get('transaction_type') == transaction_type]
                    
                    # Показываем транзакции
                    for transaction in filtered_transactions[:20]:
                        # Определяем цвет и заголовок по типу
                        type_config = {
                            'deposit': {'color': '#4CAF50', 'title': 'Пополнение'},
                            'subscription_purchase': {'color': '#2196F3', 'title': 'Покупка подписки'},
                            'subscription_renewal': {'color': '#FF9800', 'title': 'Продление подписки'},
                            'subscription_auto_renewal': {'color': '#FF5722', 'title': 'Автопродление'},
                            'refund': {'color': '#9C27B0', 'title': 'Возврат средств'}
                        }
                        
                        config = type_config.get(
                            transaction.get('transaction_type', ''),
                            {'color': '#757575', 'title': 'Операция'}
                        )
                        
                        # Форматируем дату
                        try:
                            created_at = datetime.fromisoformat(
                                transaction.get('created_at', '').replace('Z', '+00:00')
                            ).strftime('%d.%m.%Y %H:%M')
                        except:
                            created_at = transaction.get('created_at', '')
                        
                        # Определяем цвет суммы
                        amount_color = '#4CAF50' if transaction.get('transaction_type') == 'deposit' else '#F44336'
                        amount_sign = '+' if transaction.get('transaction_type') == 'deposit' else '-'
                        
                        # Отображаем транзакцию
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{config['title']}**")
                            st.caption(f"{created_at}")
                        
                        with col2:
                            description = transaction.get('description', '')
                            if len(description) > 50:
                                description = description[:50] + "..."
                            st.write(description)
                        
                        with col3:
                            st.markdown(f"<span style='color:{amount_color}; font-weight:bold;'>{amount_sign}{transaction.get('amount')} руб.</span>", 
                                      unsafe_allow_html=True)
                            
                            status_text = transaction.get('status', 'unknown')
                            status_display = "Выполнено" if transaction.get('status') == 'completed' else "В процессе"
                            st.caption(f"{status_display}")
                        
                        st.divider()
                    
                    if len(filtered_transactions) > 20:
                        st.info(f"Показаны последние 20 операций из {len(filtered_transactions)}")
                else:
                    st.info("У вас пока нет операций. Пополните баланс или купите первую подписку!")
            else:
                st.error("Ошибка загрузки истории операций")
                
        else:
            st.error("Ошибка загрузки баланса")
            
    except requests.exceptions.ConnectionError:
        st.error("Ошибка подключения к серверу. Проверьте, запущен ли бэкенд.")
    except Exception as e:
        st.error(f"Ошибка: {str(e)}")
    
    # Информационный блок
    with st.expander("Информация о балансе"):
        st.markdown("""
        **Как работает баланс:**
        
        1. **Пополнение** - вы можете пополнить баланс любой суммой от 0 рублей
        2. **Автопродление** - при включенном авто-продлении средства списываются автоматически за 24 часа до окончания подписки
        3. **Возвраты** - возвращенные средства зачисляются на баланс
        4. **Безопасность** - все операции защищены и логируются
        
        **Что можно оплатить с баланса:**
        - Покупка новых подписок
        - Автоматическое продление подписок
        - Частичная оплата (если доступно)
        
        **Минимальная сумма:** 0 руб.
        **Максимальный баланс:** 50,000 руб.
        
        **Как работают автоплатежи:**
        - Система проверяет подписки каждые 5 минут (в тестовом режиме)
        - Если подписка заканчивается в течение 24 часов и включено автопродление
        - Проверяется достаточность средств на балансе
        - Средства списываются автоматически
        - Подписка продлевается на следующий период
        - При недостатке средств отправляется уведомление
        """)

if __name__ == "__main__":
    main()