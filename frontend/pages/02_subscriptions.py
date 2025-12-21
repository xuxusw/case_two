import streamlit as st
import requests
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000/api"

st.set_page_config(
    page_title="Управление подписками",
    page_icon=":chart_with_upwards_trend:",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        color: #388E3C;
        padding-bottom: 1rem;
        border-bottom: 2px solid #4CAF50;
    }
    .subscription-card {
        background-color: #F5F5F5;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 1rem;
    }
    .plan-card {
        background-color: white;
        border: 2px solid #E0E0E0;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    .plan-card:hover {
        border-color: #4CAF50;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .price-badge {
        background-color: #4CAF50;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.2rem;
        margin: 1rem 0;
    }
    .status-active {
        color: #4CAF50;
        font-weight: bold;
    }
    .status-expired {
        color: #F44336;
        font-weight: bold;
    }
    .status-pending {
        color: #FF9800;
        font-weight: bold;
    }
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
        st.error(f"Ошибка загрузки тарифов: {e}")
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
        st.error(f"Ошибка загрузки подписок: {e}")
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
        st.error(f"Ошибка загрузки промокодов: {e}")
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
        st.error(f"Ошибка загрузки транзакций: {e}")
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
        st.error(f"Ошибка покупки подписки: {e}")
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
        st.error(f"Ошибка отмены подписки: {e}")
        return None

def format_date(date_string):
    if not date_string:
        return "Не указано"
    try:
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_string

def format_price(price):
    """Форматирование цены"""
    try:
        # Преобразуем строку в число если нужно
        if isinstance(price, str):
            price = float(price)
        return f"{price:.2f} RUB"
    except (ValueError, TypeError):
        # Если не удается преобразовать, возвращаем как есть
        return f"{price} RUB"

def display_plan_card(plan, on_select):
    with st.container():
        # Получаем отформатированную цену
        formatted_price = format_price(plan['price'])
        
        st.markdown(f"""
        <div class="plan-card">
            <h3>{plan['name']}</h3>
            <p>{plan['description']}</p>
            <div class="price-badge">{formatted_price}</div>
            <p><strong>Продолжительность:</strong> {plan['duration_days']} дней</p>
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
        # ИСПРАВЛЕНИЕ: Получаем данные из правильных полей
        # subscription['plan'] - это ID (число), а не объект
        # Используем plan_name и plan_price которые уже есть в данных
        plan_name = subscription.get('plan_name', 'Неизвестный тариф')
        plan_price = subscription.get('plan_price', 0)
        
        # Если есть вложенный объект plan (старый формат)
        if 'plan' in subscription and isinstance(subscription['plan'], dict):
            plan_name = subscription['plan'].get('name', plan_name)
            plan_price = subscription['plan'].get('price', plan_price)
        elif 'plan' in subscription and isinstance(subscription['plan'], (int, str)):
            # Если plan это ID, оставляем имя по умолчанию
            pass
        
        formatted_price = format_price(plan_price)
        
        st.markdown(f"""
        <div class="subscription-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3>{plan_name}</h3>
                    <p><span class="{status_class}">{status_text}</span></p>
                </div>
                <div style="text-align: right;">
                    <p><strong>Цена:</strong> {formatted_price}</p>
                </div>
            </div>
            <div style="margin-top: 1rem;">
                <p><strong>Начало:</strong> {format_date(subscription.get('start_date'))}</p>
                <p><strong>Окончание:</strong> {format_date(subscription.get('end_date'))}</p>
                <p><strong>Автопродление:</strong> {'Включено' if subscription.get('auto_renew', False) else 'Выключено'}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if subscription.get('status') == 'active':
                if st.button("Отменить подписку", key=f"cancel_{subscription['id']}"):
                    response = cancel_subscription(subscription['id'])
                    if response and response.status_code == 200:
                        st.success("Подписка отменена")
                        st.rerun()
                    elif response:
                        st.error(f"Ошибка: {response.status_code} - {response.text}")
                    else:
                        st.error("Ошибка отмены подписки")
        with col2:
            if subscription.get('status') == 'expired':
                if st.button("Продлить", key=f"renew_{subscription['id']}"):
                    st.info("Функция продления будет доступна в следующем обновлении")

def main():
    if st.button("На главную", key="back_home"):
        st.switch_page("app.py")
    
    if 'access_token' not in st.session_state:
        st.warning("Пожалуйста, войдите в систему")
        if st.button("Перейти к авторизации", use_container_width=True):
            st.switch_page("pages/01_auth.py")
        return
    
    user = st.session_state.get('user', {})
    
    st.markdown(f"<h1 class='main-header'>Управление подписками</h1>", unsafe_allow_html=True)
    st.markdown(f"**Пользователь:** {user.get('username', '')} | **Роль:** {user.get('role', '')}")
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "Доступные тарифы",
        "Мои подписки",
        "История операций",
        "Промокоды"
    ])
    
    with tab1:
        st.header("Доступные тарифные планы")
        
        plans = fetch_subscription_plans()
        
        if not plans:
            st.info("Нет доступных тарифных планов")
        else:
            col1, col2 = st.columns([3, 1])
            with col2:
                sort_by = st.selectbox("Сортировать по:", ["Цена (возр.)", "Цена (убыв.)", "Длительность"])
            
            # Сортировка с преобразованием цены в число
            if sort_by == "Цена (возр.)":
                plans = sorted(plans, key=lambda x: float(x['price']) if isinstance(x['price'], str) else x['price'])
            elif sort_by == "Цена (убыв.)":
                plans = sorted(plans, key=lambda x: float(x['price']) if isinstance(x['price'], str) else x['price'], reverse=True)
            
            # ИСПРАВЛЕНИЕ: Убедимся, что есть хотя бы 1 колонка
            num_cols = max(1, min(3, len(plans)))
            cols = st.columns(num_cols)
            selected_plan = None
            
            for idx, plan in enumerate(plans):
                with cols[idx % num_cols]:
                    display_plan_card(plan, lambda p: st.session_state.update({'selected_plan': p}))
            
            if 'selected_plan' in st.session_state:
                st.markdown("---")
                selected_plan = st.session_state['selected_plan']
                
                st.subheader(f"Подписаться на: {selected_plan['name']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Описание:** {selected_plan['description']}")
                    st.markdown(f"**Цена:** {format_price(selected_plan['price'])}")
                    st.markdown(f"**Длительность:** {selected_plan['duration_days']} дней")
                
                with col2:
                    promocodes = fetch_promocodes()
                    valid_promocodes = [p for p in promocodes if p.get('is_valid', False)]
                    
                    promo_options = ["Без промокода"] + [f"{p['code']} (-{p['discount_percent']}%)" for p in valid_promocodes]
                    selected_promo = st.selectbox("Промокод", promo_options, key="promo_select_1")
                    
                    promo_code = ""
                    if selected_promo != "Без промокода":
                        promo_code = selected_promo.split(" ")[0]
                        promo = next(p for p in valid_promocodes if p['code'] == promo_code)
                        discount = promo['discount_percent']
                        # Преобразуем цену в число для расчетов
                        price_num = float(selected_plan['price']) if isinstance(selected_plan['price'], str) else selected_plan['price']
                        final_price = price_num * (100 - discount) / 100
                        st.info(f"Цена со скидкой: **{format_price(final_price)}** (-{discount}%)")
                
                if st.button("Подписаться", type="primary", use_container_width=True, key="subscribe_btn_1"):
                    with st.spinner("Обработка платежа..."):
                        response = purchase_subscription(selected_plan['id'], promo_code)
                        
                        if response:
                            if response.status_code == 201:
                                data = response.json()
                                st.success("Подписка успешно оформлена")
                                
                                st.markdown(f"**ID подписки:** {data.get('subscription_id')}")
                                st.markdown(f"**ID транзакции:** {data.get('transaction_id')}")
                                if data.get('end_date'):
                                    st.markdown(f"**Действует до:** {format_date(data.get('end_date'))}")
                                
                                if 'selected_plan' in st.session_state:
                                    del st.session_state['selected_plan']
                                st.rerun()
                            elif response.status_code == 402:
                                data = response.json()
                                st.error(f"Ошибка платежа: {data.get('message', 'Неизвестная ошибка')}")
                            else:
                                st.error(f"Ошибка: {response.status_code} - {response.text}")
    
    with tab2:
        st.header("Мои подписки")
        
        status_filter = st.selectbox(
            "Фильтр по статусу",
            ["Все", "Активные", "Истекшие", "Отмененные", "Ожидают оплаты"],
            key="status_filter_1"
        )
        
        subscriptions = fetch_my_subscriptions()
        
        if not subscriptions:
            st.info("У вас нет активных подписок")
        else:
            filtered_subs = subscriptions
            if status_filter == "Активные":
                filtered_subs = [s for s in subscriptions if s.get('status') == 'active']
            elif status_filter == "Истекшие":
                filtered_subs = [s for s in subscriptions if s.get('status') == 'expired']
            elif status_filter == "Отмененные":
                filtered_subs = [s for s in subscriptions if s.get('status') == 'canceled']
            elif status_filter == "Ожидают оплаты":
                filtered_subs = [s for s in subscriptions if s.get('status') == 'pending']
            
            active_count = len([s for s in subscriptions if s.get('status') == 'active'])
            total_count = len(subscriptions)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Всего подписок", total_count)
            col2.metric("Активных", active_count)
            if total_count > 0:
                col3.metric("Процент активных", f"{(active_count/total_count*100):.1f}%")
            
            st.markdown("---")
            
            for subscription in filtered_subs:
                display_subscription_card(subscription)
    
    with tab3:
        st.header("История операций")
        
        transactions = fetch_transactions()
        
        if not transactions:
            st.info("Нет данных о транзакциях")
        else:
            table_data = []
            for t in transactions:
                table_data.append({
                    "Дата": format_date(t.get('created_at')),
                    "Тип": t.get('transaction_type', '').replace('_', ' ').title(),
                    "Сумма": format_price(t.get('amount', 0)),
                    "Статус": t.get('status', '').title(),
                    "Описание": t.get('description', '')
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
            
            st.markdown("---")
            st.subheader("Статистика")
            
            successful = len([t for t in transactions if t.get('status') == 'completed'])
            failed = len([t for t in transactions if t.get('status') == 'failed'])
            
            # Суммируем с преобразованием в число
            total_amount = 0
            for t in transactions:
                if t.get('status') == 'completed':
                    try:
                        amount = t.get('amount', 0)
                        if isinstance(amount, str):
                            amount = float(amount)
                        total_amount += amount
                    except (ValueError, TypeError):
                        pass
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Успешных операций", successful)
            col2.metric("Неудачных", failed)
            col3.metric("Общая сумма", f"{total_amount:.2f} RUB")
    
    with tab4:
        st.header("Доступные промокоды")
        
        promocodes = fetch_promocodes()
        
        if not promocodes:
            st.info("Нет доступных промокодов")
        else:
            show_only_valid = st.checkbox("Показывать только действующие", value=True, key="show_valid_promo")
            
            if show_only_valid:
                promocodes = [p for p in promocodes if p.get('is_valid', False)]
            
            # ИСПРАВЛЕНИЕ: Проверяем, что promocodes не пустой после фильтрации
            if promocodes:
                # Используем минимум 1 колонку
                num_cols = max(1, min(3, len(promocodes)))
                cols = st.columns(num_cols)
                
                for idx, promo in enumerate(promocodes):
                    with cols[idx % num_cols]:
                        border_color = "#4CAF50" if promo.get('is_valid', False) else "#9E9E9E"
                        
                        st.markdown(f"""
                        <div style="
                            border: 2px solid {border_color};
                            border-radius: 10px;
                            padding: 1rem;
                            margin-bottom: 1rem;
                            background-color: white;
                            text-align: center;
                        ">
                            <h3 style="color: #388E3C;">{promo.get('code', 'Неизвестно')}</h3>
                            <p><strong>Скидка:</strong> {promo.get('discount_percent', 0)}%</p>
                            <p><small>{promo.get('description', '')}</small></p>
                            <p><strong>Использовано:</strong> {promo.get('used_count', 0)}/{promo.get('max_uses', 1)}</p>
                            <p><strong>Действует до:</strong> {format_date(promo.get('valid_to'))}</p>
                            <p><strong>Статус:</strong> {'Действует' if promo.get('is_valid', False) else 'Недействителен'}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Нет действующих промокодов")
            
            st.markdown("---")
            st.info("Как использовать промокод: Выберите промокод при оформлении подписки во вкладке 'Доступные тарифы'. Скидка будет применена автоматически.")
    
    with st.sidebar:
        st.markdown("### Быстрые действия")
        
        if st.button("Обновить данные", use_container_width=True, key="refresh_btn"):
            st.rerun()
        
        if st.button("Выйти", use_container_width=True, key="logout_btn"):
            for key in ['access_token', 'refresh_token', 'user']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()