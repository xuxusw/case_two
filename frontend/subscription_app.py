import streamlit as st
import requests
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000/api"
BACKGROUND_COLOR = "#FFFFFF"
ACCENT_COLOR = "#4CAF50"
SECONDARY_COLOR = "#388E3C"
TEXT_COLOR = "#333333"
LIGHT_GRAY = "#F5F5F5"

st.set_page_config(
    page_title="Управление подписками",
    layout="wide"
)

# Кастомный CSS
st.markdown(f"""
<style>
    .stApp {{
        background-color: {BACKGROUND_COLOR};
    }}
    .main-header {{
        color: {SECONDARY_COLOR};
        padding-bottom: 1rem;
        border-bottom: 2px solid {ACCENT_COLOR};
    }}
    .subscription-card {{
        background-color: {LIGHT_GRAY};
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid {ACCENT_COLOR};
        margin-bottom: 1rem;
    }}
    .plan-card {{
        background-color: white;
        border: 2px solid #E0E0E0;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }}
    .plan-card:hover {{
        border-color: {ACCENT_COLOR};
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    .price-badge {{
        background-color: {ACCENT_COLOR};
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.2rem;
        margin: 1rem 0;
    }}
    .status-active {{
        color: {ACCENT_COLOR};
        font-weight: bold;
    }}
    .status-expired {{
        color: #F44336;
        font-weight: bold;
    }}
    .status-pending {{
        color: #FF9800;
        font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)

def get_auth_headers():
    if 'access_token' not in st.session_state:
        return None
    return {
        'Authorization': f'Bearer {st.session_state["access_token"]}',
        'Content-Type': 'application/json'
    }

def fetch_subscription_plans():
    try:
        response = requests.get(f"{API_BASE_URL}/subscriptions/plans/")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Ошибка при загрузке планов: {e}")
        return []

def fetch_my_subscriptions():
    headers = get_auth_headers()
    if not headers:
        return []
    
    try:
        response = requests.get(f"{API_BASE_URL}/subscriptions/my-subscriptions/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Ошибка при загрузке подписок: {e}")
        return []

def fetch_promocodes():
    headers = get_auth_headers()
    if not headers:
        return []
    
    try:
        response = requests.get(f"{API_BASE_URL}/subscriptions/promocodes/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Ошибка при загрузке промокодов: {e}")
        return []

def fetch_transactions():
    headers = get_auth_headers()
    if not headers:
        return []
    
    try:
        response = requests.get(f"{API_BASE_URL}/subscriptions/transactions/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Ошибка при загрузке транзакций: {e}")
        return []

def purchase_subscription(plan_id, promo_code=""):
    headers = get_auth_headers()
    if not headers:
        return None
    
    data = {"plan_id": plan_id}
    if promo_code:
        data["promo_code"] = promo_code
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/subscriptions/purchase/",
            json=data,
            headers=headers
        )
        return response
    except Exception as e:
        st.error(f"Ошибка при оформлении подписки: {e}")
        return None

def cancel_subscription(subscription_id):
    headers = get_auth_headers()
    if not headers:
        return None
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/subscriptions/my-subscriptions/{subscription_id}/cancel/",
            headers=headers
        )
        return response
    except Exception as e:
        st.error(f"Ошибка при отмене подписки: {e}")
        return None

def format_date(date_string):
    if not date_string:
        return "Не указана"
    try:
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_string

def format_price(price):
    return f"{price:.2f} руб."

def display_plan_card(plan, on_select):
    with st.container():
        st.markdown(f"""
        <div class="plan-card">
            <h3>{plan['name']}</h3>
            <p>{plan['description']}</p>
            <div class="price-badge">{format_price(plan['price'])}</div>
            <p><strong>Срок:</strong> {plan['duration_days']} дней</p>
        </div>
        """, unsafe_allow_html=True)
        
        if on_select:
            if st.button(f"Выбрать {plan['name']}", key=f"select_{plan['id']}"):
                on_select(plan)

def display_subscription_card(subscription):
    status_class = f"status-{subscription['status']}"
    status_text = {
        'active': 'Активна',
        'expired': 'Истекла',
        'pending': 'Ожидает оплаты',
        'canceled': 'Отменена',
        'pending_renewal': 'Ожидает продления'
    }.get(subscription['status'], subscription['status'])
    
    with st.container():
        st.markdown(f"""
        <div class="subscription-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3>{subscription['plan']['name']}</h3>
                    <p><span class="{status_class}">{status_text}</span></p>
                </div>
                <div style="text-align: right;">
                    <p><strong>Стоимость:</strong> {format_price(subscription['plan']['price'])}</p>
                </div>
            </div>
            <div style="margin-top: 1rem;">
                <p><strong>Начало:</strong> {format_date(subscription['start_date'])}</p>
                <p><strong>Окончание:</strong> {format_date(subscription['end_date'])}</p>
                <p><strong>Осталось дней:</strong> {subscription.get('days_remaining', 0)}</p>
                <p><strong>Автопродление:</strong> {'Включено' if subscription['auto_renew'] else 'Выключено'}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Кнопки действий для активных подписок
        col1, col2 = st.columns(2)
        with col1:
            if subscription['status'] == 'active':
                if st.button("Отменить подписку", key=f"cancel_{subscription['id']}"):
                    response = cancel_subscription(subscription['id'])
                    if response and response.status_code == 200:
                        st.success("Подписка отменена")
                        st.rerun()
                    else:
                        st.error("Ошибка при отмене подписки")
        with col2:
            if subscription['status'] == 'expired':
                if st.button("Продлить", key=f"renew_{subscription['id']}"):
                    st.info("Функция продления будет доступна в следующем обновлении")

def main():
    
    # Проверка авторизации
    if 'access_token' not in st.session_state:
        st.warning("Пожалуйста, войдите в систему")
        st.page_link("frontend/auth_app.py", label="Перейти к авторизации", icon="🔐")
        return
    
    user = st.session_state.get('user', {})
    
    # Главный заголовок
    st.markdown(f"<h1 class='main-header'>📊 Управление подписками</h1>", unsafe_allow_html=True)
    st.markdown(f"**Пользователь:** {user.get('username', '')} | **Роль:** {user.get('role', '')}")
    st.markdown("---")
    
    # вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "Доступные планы",
        "Мои подписки",
        "История транзакций",
        "Промокоды"
    ])
    
    # Вкладка 1: Доступные планы
    with tab1:
        st.header("Доступные планы подписок")
        
        plans = fetch_subscription_plans()
        
        if not plans:
            st.info("Нет доступных планов подписок")
        else:
            # Фильтр по цене
            col1, col2 = st.columns([3, 1])
            with col2:
                sort_by = st.selectbox("Сортировать по:", ["Цене (возр.)", "Цене (убыв.)", "Длительности"])
            
            # Сортировка
            if sort_by == "Цене (возр.)":
                plans = sorted(plans, key=lambda x: x['price'])
            elif sort_by == "Цене (убыв.)":
                plans = sorted(plans, key=lambda x: x['price'], reverse=True)
            
            # Отображаем планы в колонках
            cols = st.columns(min(3, len(plans)))
            selected_plan = None
            
            for idx, plan in enumerate(plans):
                with cols[idx % len(cols)]:
                    display_plan_card(plan, lambda p: st.session_state.update({'selected_plan': p}))
            
            # Если план выбран, показываем форму покупки
            if 'selected_plan' in st.session_state:
                st.markdown("---")
                selected_plan = st.session_state['selected_plan']
                
                st.subheader(f"Оформление подписки: {selected_plan['name']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Описание:** {selected_plan['description']}")
                    st.markdown(f"**Цена:** {format_price(selected_plan['price'])}")
                    st.markdown(f"**Длительность:** {selected_plan['duration_days']} дней")
                
                with col2:
                    # Выбор промокода
                    promocodes = fetch_promocodes()
                    valid_promocodes = [p for p in promocodes if p.get('is_valid', False)]
                    
                    promo_options = ["Без промокода"] + [f"{p['code']} (-{p['discount_percent']}%)" for p in valid_promocodes]
                    selected_promo = st.selectbox("Промокод", promo_options)
                    
                    promo_code = ""
                    if selected_promo != "Без промокода":
                        promo_code = selected_promo.split(" ")[0]
                        # Показываем итоговую цену со скидкой
                        promo = next(p for p in valid_promocodes if p['code'] == promo_code)
                        discount = promo['discount_percent']
                        final_price = selected_plan['price'] * (100 - discount) / 100
                        st.info(f"Цена со скидкой: **{format_price(final_price)}** (-{discount}%)")
                
                # Кнопка покупки
                if st.button("Оформить подписку", type="primary", use_container_width=True):
                    with st.spinner("Обработка платежа..."):
                        response = purchase_subscription(selected_plan['id'], promo_code)
                        
                        if response:
                            if response.status_code == 201:
                                data = response.json()
                                st.success("Подписка успешно оформлена!")
                                st.balloons()
                                
                                # Показываем детали
                                st.markdown(f"**ID подписки:** {data.get('subscription_id')}")
                                st.markdown(f"**ID транзакции:** {data.get('transaction_id')}")
                                if data.get('end_date'):
                                    st.markdown(f"**Действует до:** {format_date(data.get('end_date'))}")
                                
                                # Очищаем выбранный план
                                if 'selected_plan' in st.session_state:
                                    del st.session_state['selected_plan']
                                st.rerun()
                            elif response.status_code == 402:
                                data = response.json()
                                st.error(f"Ошибка платежа: {data.get('message', 'Неизвестная ошибка')}")
                            else:
                                st.error(f"Ошибка: {response.status_code} - {response.text}")
    
    # Вкладка 2: Мои подписки
    with tab2:
        st.header("Мои подписки")
        
        # Фильтр по статусу
        status_filter = st.selectbox(
            "Фильтр по статусу",
            ["Все", "Активные", "Истекшие", "Отмененные", "Ожидающие оплаты"]
        )
        
        # Загружаем подписки
        subscriptions = fetch_my_subscriptions()
        
        if not subscriptions:
            st.info("У вас нет активных подписок")
        else:
            # Применяем фильтр
            filtered_subs = subscriptions
            if status_filter == "Активные":
                filtered_subs = [s for s in subscriptions if s['status'] == 'active']
            elif status_filter == "Истекшие":
                filtered_subs = [s for s in subscriptions if s['status'] == 'expired']
            elif status_filter == "Отмененные":
                filtered_subs = [s for s in subscriptions if s['status'] == 'canceled']
            elif status_filter == "Ожидающие оплаты":
                filtered_subs = [s for s in subscriptions if s['status'] == 'pending']
            
            # Показываем статистику
            active_count = len([s for s in subscriptions if s['status'] == 'active'])
            total_count = len(subscriptions)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Всего подписок", total_count)
            col2.metric("Активных", active_count)
            if total_count > 0:
                col3.metric("Активных %", f"{(active_count/total_count*100):.1f}%")
            
            st.markdown("---")
            
            # Отображаем подписки
            for subscription in filtered_subs:
                display_subscription_card(subscription)
    
    # Вкладка 3: История транзакций
    with tab3:
        st.header("История транзакций")
        
        transactions = fetch_transactions()
        
        if not transactions:
            st.info("Нет данных о транзакциях")
        else:
            # Таблица транзакций
            table_data = []
            for t in transactions:
                table_data.append({
                    "Дата": format_date(t['created_at']),
                    "Тип": t['transaction_type'].replace('_', ' ').title(),
                    "Сумма": format_price(t['amount']),
                    "Статус": t['status'].title(),
                    "Описание": t['description']
                })
            
            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Дата": st.column_config.TextColumn("Дата"),
                    "Тип": st.column_config.TextColumn("Тип операции"),
                    "Сумма": st.column_config.TextColumn("Сумма"),
                    "Статус": st.column_config.TextColumn("Статус"),
                    "Описание": st.column_config.TextColumn("Описание", width="large")
                }
            )
            
            # Статистика по транзакциям
            st.markdown("---")
            st.subheader("Статистика")
            
            successful = len([t for t in transactions if t['status'] == 'completed'])
            failed = len([t for t in transactions if t['status'] == 'failed'])
            total_amount = sum(float(t['amount']) for t in transactions if t['status'] == 'completed')
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Успешных операций", successful)
            col2.metric("Неуспешных", failed)
            col3.metric("Общая сумма", f"{total_amount:.2f} руб.")
    
    # Вкладка 4: Промокоды
    with tab4:
        st.header("Доступные промокоды")
        
        promocodes = fetch_promocodes()
        
        if not promocodes:
            st.info("Нет доступных промокодов")
        else:
            # Фильтр по валидности
            show_only_valid = st.checkbox("Показывать только действующие", value=True)
            
            if show_only_valid:
                promocodes = [p for p in promocodes if p.get('is_valid', False)]
            
            # Отображаем промокоды
            cols = st.columns(min(3, len(promocodes)))
            
            for idx, promo in enumerate(promocodes):
                with cols[idx % len(cols)]:
                    # Определяем цвет карточки в зависимости от валидности
                    border_color = ACCENT_COLOR if promo.get('is_valid', False) else "#9E9E9E"
                    
                    st.markdown(f"""
                    <div style="
                        border: 2px solid {border_color};
                        border-radius: 10px;
                        padding: 1rem;
                        margin-bottom: 1rem;
                        background-color: white;
                        text-align: center;
                    ">
                        <h3 style="color: {SECONDARY_COLOR};">{promo['code']}</h3>
                        <p><strong>Скидка:</strong> {promo['discount_percent']}%</p>
                        <p><small>{promo['description']}</small></p>
                        <p><strong>Использовано:</strong> {promo['used_count']}/{promo['max_uses']}</p>
                        <p><strong>Действует до:</strong> {format_date(promo['valid_to'])}</p>
                        <p><strong>Статус:</strong> {'Действует' if promo.get('is_valid', False) else 'Недействителен'}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.info("**Как использовать промокод:**\n\nВыберите промокод при оформлении подписки во вкладке 'Доступные планы'. Скидка будет применена автоматически.")
    
    # Сайдбар с дополнительной информацией
    with st.sidebar:
        st.markdown("### Быстрые действия")
        
        if st.button("Обновить данные", use_container_width=True):
            st.rerun()
        
        if st.button("Выйти из системы", use_container_width=True):
            for key in ['access_token', 'refresh_token', 'user']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        st.markdown("###Справка")
        st.markdown("""
        **Автопродление:**  
        Подписки с включенным автопродлением будут автоматически продлеваться за день до окончания.
        
        **Отмена подписки:**  
        Отмена активной подписки прекращает автопродление, но текущий период действует до конца.
        
        **Возвраты:**  
        Возврат средств возможен в течение 24 часов после покупки.
        """)

if __name__ == "__main__":
    main()