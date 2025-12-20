import streamlit as st
import requests
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000/api"

st.set_page_config(
    page_title="Тест продления",
    layout="wide"
)

def get_auth_headers():
    if 'access_token' not in st.session_state:
        return None
    return {
        'Authorization': f'Bearer {st.session_state["access_token"]}',
        'Content-Type': 'application/json'
    }

def main():
    st.title("Тестирование автоматического продления")
    
    if 'access_token' not in st.session_state:
        st.warning("Пожалуйста, войдите в систему")
        if st.button("Войти", use_container_width=True):
            st.switch_page("pages/01_auth.py")
        return
    
    headers = get_auth_headers()
    
    st.markdown("---")
    
    # Раздел 1: Быстрое создание тестовой подписки
    st.header("Быстрый тест")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("1. Создать тестовую подписку", type="primary", use_container_width=True):
            with st.spinner("Создаем подписку..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/subscriptions/purchase/",
                        json={"plan_id": 1},
                        headers=headers
                    )
                    
                    if response.status_code == 201:
                        data = response.json()
                        st.success(f"Подписка создана! ID: {data.get('subscription_id')}")
                        st.rerun()
                    else:
                        st.error(f"Ошибка: {response.text}")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    
    with col2:
        if st.button("2. Продлить ВСЕ мои подписки", type="secondary", use_container_width=True):
            with st.spinner("Продлеваем подписки..."):
                try:
                    # Получаем все подписки
                    subs_response = requests.get(
                        f"{API_BASE_URL}/subscriptions/my-subscriptions/",
                        headers=headers
                    )
                    
                    if subs_response.status_code == 200:
                        subscriptions = subs_response.json()
                        renewed_count = 0
                        
                        for sub in subscriptions:
                            # Продлеваем каждую подписку
                            renew_response = requests.post(
                                f"{API_BASE_URL}/subscriptions/test-renew/{sub['id']}/",
                                headers=headers
                            )
                            
                            if renew_response.status_code == 200:
                                renewed_count += 1
                        
                        st.success(f"Продлено {renewed_count} из {len(subscriptions)} подписок")
                        st.rerun()
                    else:
                        st.error("Ошибка загрузки подписок")
                        
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    
    st.markdown("---")
    
    # Раздел 2: Мои подписки
    st.header("Мои подписки")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/subscriptions/my-subscriptions/",
            headers=headers
        )
        
        if response.status_code == 200:
            subscriptions = response.json()
            
            if not subscriptions:
                st.info("У вас нет подписок. Создайте тестовую подписку выше.")
            else:
                for sub in subscriptions:
                    with st.expander(f"Подписка #{sub['id']} - {sub['plan']['name']} ({sub['status']})"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"**План:** {sub['plan']['name']}")
                            st.write(f"**Цена:** {sub['plan']['price']} RUB")
                            st.write(f"**Начало:** {sub['start_date'][:10] if sub['start_date'] else 'Нет'}")
                            st.write(f"**Окончание:** {sub['end_date'][:10] if sub['end_date'] else 'Нет'}")
                            st.write(f"**Статус:** {sub['status']}")
                            st.write(f"**Автопродление:** {'Да' if sub['auto_renew'] else 'Нет'}")
                        
                        with col2:
                            # Кнопка продлить эту подписку
                            if st.button(f"Продлить #{sub['id']}", key=f"renew_{sub['id']}"):
                                with st.spinner("Продление..."):
                                    renew_response = requests.post(
                                        f"{API_BASE_URL}/subscriptions/test-renew/{sub['id']}/",
                                        headers=headers
                                    )
                                    
                                    if renew_response.status_code == 200:
                                        st.success("Подписка продлена!")
                                        st.rerun()
                                    else:
                                        st.error(f"Ошибка: {renew_response.text}")
                        
                        with col3:
                            # Кнопка изменить дату окончания
                            if st.button(f"Изменить дату #{sub['id']}", key=f"update_{sub['id']}"):
                                minutes = st.number_input(
                                    "Через сколько минут закончится:",
                                    min_value=1,
                                    max_value=1440,
                                    value=30,
                                    key=f"minutes_{sub['id']}"
                                )
                                
                                if st.button("Подтвердить", key=f"confirm_{sub['id']}"):
                                    update_response = requests.post(
                                        f"{API_BASE_URL}/subscriptions/test/update-end-date/{sub['id']}/",
                                        json={"minutes": minutes},
                                        headers=headers
                                    )
                                    
                                    if update_response.status_code == 200:
                                        st.success("Дата обновлена!")
                                        st.rerun()
                                    else:
                                        st.error(f"Ошибка: {update_response.text}")
        else:
            st.error("Ошибка загрузки подписок")
    except Exception as e:
        st.error(f"Ошибка: {e}")
    
    st.markdown("---")
    
    # Раздел 3: История транзакций
    st.header("История транзакций")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/subscriptions/transactions/",
            headers=headers
        )
        
        if response.status_code == 200:
            transactions = response.json()
            
            if not transactions:
                st.info("Нет транзакций")
            else:
                # Показываем последние 10 транзакций
                for t in transactions[:10]:
                    if t['status'] == 'completed':
                        color = "green"
                    elif t['status'] == 'failed':
                        color = "red"
                    else:
                        color = "orange"
                    
                    # Форматируем дату
                    created_at = t['created_at']
                    if created_at:
                        try:
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_str = dt.strftime("%d.%m.%Y %H:%M")
                        except:
                            date_str = created_at[:16]
                    else:
                        date_str = "Неизвестно"
                    
                    # Отображаем транзакцию
                    st.markdown(f"""
                    <div style="
                        padding: 10px;
                        margin: 5px 0;
                        border-left: 4px solid {color};
                        background-color: #f9f9f9;
                    ">
                        Сумма: <strong>{t['amount']} RUB</strong><br>
                        Статус: {t['status']}<br>
                        Дата: {date_str}<br>
                        <small>{t['description']}</small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.error("Ошибка загрузки транзакций")
    except Exception as e:
        st.error(f"Ошибка: {e}")
    
    # Раздел 4: Информация
    st.markdown("---")
    st.info("""
    **Как работает тест:**
    1. Создайте подписку кнопкой выше
    2. Нажмите "Продлить" для конкретной подписки
    3. Или измените дату окончания, чтобы увидеть работу автоматического продления
    4. Проверьте историю транзакций - там будут записи о продлениях
    5. Дополнительно можно отменить подписку во вкладке subsсriptions/My subscriptions,
        а затем вернуться и продлить в этой вкладке теста
    """)

if __name__ == "__main__":
    main()