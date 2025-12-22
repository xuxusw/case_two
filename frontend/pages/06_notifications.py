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
        page_title="Мои уведомления",
        page_icon="",
        layout="wide"
    )
    
    if 'access_token' not in st.session_state:
        st.error("Вы не авторизованы")
        if st.button("Войти в систему"):
            st.switch_page("pages/01_auth.py")
        return
    
    headers = get_auth_headers()
    
    st.title("Мои уведомления")
    st.markdown("---")
    
    # Загружаем уведомления пользователя
    try:
        response = requests.get(
            f"{API_BASE_URL}/subscriptions/notifications/",
            headers=headers
        )
        
        if response.status_code == 200:
            notifications = response.json()
            
            if notifications:
                # Фильтры
                col1, col2 = st.columns(2)
                with col1:
                    show_read = st.checkbox("Показывать прочитанные", value=False)
                with col2:
                    notification_type = st.selectbox("Тип уведомления", ["Все", "payment_success", "payment_failed", "subscription_expiring"])
                
                # Применяем фильтры
                filtered_notifications = notifications
                if not show_read:
                    filtered_notifications = [n for n in filtered_notifications if not n.get('is_read')]
                if notification_type != "Все":
                    filtered_notifications = [n for n in filtered_notifications if n.get('notification_type') == notification_type]
                
                # Счетчики
                unread_count = len([n for n in notifications if not n.get('is_read')])
                st.info(f"У вас {unread_count} непрочитанных уведомлений из {len(notifications)}")
                
                # Отображаем уведомления
                for notification in filtered_notifications:
                    # Определяем цвет и заголовок по типу
                    type_config = {
                        'payment_success': {'color': '#4CAF50', 'title': 'Успешный платеж'},
                        'payment_failed': {'color': '#F44336', 'title': 'Ошибка платежа'},
                        'subscription_expiring': {'color': '#FF9800', 'title': 'Истечение подписки'},
                        'subscription_canceled': {'color': '#9E9E9E', 'title': 'Отмена подписки'},
                        'refund_processed': {'color': '#2196F3', 'title': 'Возврат средств'}
                    }
                    
                    config = type_config.get(notification.get('notification_type', ''), {'color': '#757575', 'title': 'Уведомление'})
                    
                    # Стиль для уведомления
                    border_color = config['color']
                    background = '#FFFFFF' if notification.get('is_read') else '#F5F5F5'
                    
                    col1, col2 = st.columns([6, 1])
                    
                    with col1:
                        st.markdown(f"""
                        <div style="
                            border-left: 4px solid {border_color};
                            background-color: {background};
                            padding: 15px;
                            margin: 10px 0;
                            border-radius: 5px;
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="color: {border_color};">{config['title']}</strong>
                                    <p style="margin: 5px 0;">{notification.get('message', '')}</p>
                                    <small style="color: #666;">
                                        {datetime.fromisoformat(notification.get('created_at', '').replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M')}
                                    </small>
                                </div>
                                {'<span style="color: #666; font-size: 12px;">Прочитано</span>' if notification.get('is_read') else ''}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if not notification.get('is_read'):
                                if st.button("Прочитать", key=f"read_{notification.get('id')}"):
                                    try:
                                        # ИСПРАВЛЕНО: изменен путь на 'mark-as-read'
                                        mark_response = requests.post(
                                            f"{API_BASE_URL}/subscriptions/notifications/{notification.get('id')}/mark-as-read/",
                                            headers=headers
                                        )
                                        if mark_response.status_code == 200:
                                            st.rerun() # Страница обновится и уведомление станет "прочитанным"
                                        else:
                                            st.error(f"Ошибка: {mark_response.status_code}")
                                    except Exception as e:
                                        st.error(f"Ошибка соединения: {e}")
                
                # Кнопки действий
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Отметить все как прочитанные", use_container_width=True):
                        try:
                            # ИСПРАВЛЕНО: маршурт mark-all-as-read 
                            res = requests.post(
                                f"{API_BASE_URL}/subscriptions/notifications/mark-all-as-read/",
                                headers=headers
                            )
                            if res.status_code == 200:
                                st.success("Все уведомления прочитаны")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка: {e}")    
                with col2:
                    if st.button("Удалить прочитанные", use_container_width=True):
                        st.info("Функция будет реализована")
            else:
                st.success("У вас нет непрочитанных уведомлений!")
                st.info("Здесь будут появляться уведомления о статусе ваших подписок и платежей.")
        else:
            st.error("Ошибка загрузки уведомлений")
    except Exception as e:
        st.error(f"Ошибка: {e}")
    
    # Информация о типах уведомлений
    with st.expander("Типы уведомлений"):
        st.markdown("""
        **Система отправляет следующие уведомления:**
        
        - **Успешный платеж** (зеленый) - когда платеж за подписку прошел успешно
        - **Ошибка платежа** (красный) - когда возникла проблема с оплатой
        - **Истечение подписки** (оранжевый) - когда подписка скоро закончится
        - **Отмена подписки** (серый) - когда вы отменяете подписку
        - **Возврат средств** (синий) - когда оформлен возврат денег
        
        Все уведомления также дублируются по email.
        """)

if __name__ == "__main__":
    main()