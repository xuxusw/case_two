import streamlit as st
import requests
import json
from datetime import datetime

def main():
    st.title("Управление балансом")
    
    if 'token' not in st.session_state:
        st.warning("Пожалуйста, войдите в систему")
        return
    
    token = st.session_state.token
    headers = {'Authorization': f'Bearer {token}'}
    api_base = 'http://localhost:8000/api/users/'
    
    try:
        # Получить текущий баланс 
        response = requests.get(
            f'{api_base}balance/',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            current_balance = float(data.get('balance', 0))
            username = data.get('username', '')
            
            # Отображение баланса
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px;
                border-radius: 15px;
                color: white;
                margin-bottom: 30px;
            ">
                <h2 style="margin: 0; font-size: 1.5rem;">Ваш баланс</h2>
                <h1 style="margin: 10px 0; font-size: 3rem;">{current_balance:.2f} руб.</h1>
                <p style="margin: 0; opacity: 0.9;">Пользователь: {username}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Форма пополнения баланса
            with st.form("deposit_form", clear_on_submit=True):
                st.subheader("Пополнить баланс")
                
                amount = st.number_input(
                    "Сумма пополнения (руб.)", 
                    min_value=100.0, 
                    max_value=100000.0, 
                    value=1000.0,
                    step=100.0,
                    help="Минимальная сумма: 100 руб."
                )
                
                payment_method = st.selectbox(
                    "Способ оплаты",
                    ["Банковская карта", "ЮMoney", "QIWI", "СБП", "Криптовалюта"]
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_button = st.form_submit_button(
                        "Пополнить", 
                        type="primary",
                        use_container_width=True
                    )
                with col2:
                    if st.form_submit_button("Быстрое пополнение 1000 руб.", use_container_width=True):
                        amount = 1000.0
                
                if submit_button:
                    if amount < 100:
                        st.error("Минимальная сумма пополнения: 100 руб.")
                    else:
                        with st.spinner(f"Обработка платежа на {amount} руб..."):
                            deposit_response = requests.post(
                                f'{api_base}deposit/',
                                headers=headers,
                                json={'amount': str(amount)}
                            )
                            
                            if deposit_response.status_code == 200:
                                result = deposit_response.json()
                                st.success(f"{result['message']}")
                                
                                # Показать детали транзакции
                                with st.expander("Детали транзакции"):
                                    st.json(result)
                                
                                # Обновить баланс в session_state
                                st.session_state.balance = float(result['new_balance'])
                                st.balloons()
                                st.rerun()
                            else:
                                try:
                                    error_data = deposit_response.json()
                                    st.error(f"{error_data.get('error', 'Ошибка при пополнении баланса')}")
                                except:
                                    st.error("Ошибка при пополнении баланса")
        
        else:
            st.error("Не удалось получить информацию о балансе")
            
    except Exception as e:
        st.error(f"Ошибка соединения: {e}")
    
    # История транзакций
    st.divider()
    st.subheader("История операций")
    
    try:
        # Получаем все транзакции пользователя
        transactions_response = requests.get(
            'http://localhost:8000/api/subscriptions/transactions/',
            headers=headers
        )
        
        if transactions_response.status_code == 200:
            transactions = transactions_response.json()
            
            if transactions:
                # Фильтруем и сортируем транзакции
                deposits = [t for t in transactions if t['transaction_type'] == 'deposit']
                payments = [t for t in transactions if t['transaction_type'] == 'payment']
                refunds = [t for t in transactions if t['transaction_type'] == 'refund']
                
                # Вкладки для разных типов операций
                tab1, tab2, tab3 = st.tabs([
                    f"Все операции ({len(transactions)})",
                    f"Пополнения ({len(deposits)})",
                    f"Платежи ({len(payments) + len(refunds)})"
                ])
                
                with tab1:
                    show_transactions(transactions)
                with tab2:
                    show_transactions(deposits)
                with tab3:
                    show_transactions(payments + refunds)
            else:
                st.info("История операций пока пуста")
        else:
            st.error("Не удалось загрузить историю операций")
            
    except Exception as e:
        st.error(f"Ошибка при загрузке истории: {e}")

def show_transactions(transactions):
    """Отображение списка транзакций"""
    if not transactions:
        st.info("Нет операций этого типа")
        return
    
    # Сортируем по дате (новые сверху)
    transactions.sort(key=lambda x: x['created_at'], reverse=True)
    
    for trans in transactions:
        # Определяем цвет и иконку
        if trans['transaction_type'] == 'deposit':
            color = "#10b981"  # зеленый
            icon = "+"
            amount_text = f"+{trans['amount']} руб."
        elif trans['transaction_type'] == 'payment':
            color = "#ef4444"  # красный
            icon = "-"
            amount_text = f"-{trans['amount']} руб."
        elif trans['transaction_type'] == 'refund':
            color = "#f59e0b"  # желтый
            icon = "↩"
            amount_text = f"+{trans['amount']} руб. (возврат)"
        else:
            color = "#6b7280"
            icon = ""
            amount_text = f"{trans['amount']} руб."
        
        # Форматируем дату
        try:
            date = datetime.fromisoformat(trans['created_at'].replace('Z', '+00:00'))
            date_str = date.strftime("%d.%m.%Y %H:%M")
        except:
            date_str = trans['created_at']
        
        # Отображаем транзакцию
        st.markdown(f"""
        <div style="
            background-color: #f8fafc;
            border-left: 4px solid {color};
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2em;">{icon}</span>
                    <div>
                        <strong>{trans['description']}</strong><br>
                        <small style="color: #6b7280;">Статус: {trans['status']}</small>
                    </div>
                </div>
                <div style="text-align: right;">
                    <strong style="color: {color}; font-size: 1.1em;">{amount_text}</strong><br>
                    <small style="color: #6b7280;">{date_str}</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()