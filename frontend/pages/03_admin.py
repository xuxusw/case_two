# frontend/pages/03_admin.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def is_admin_user():
    # проверка является ли пользователь админом
    if 'user' not in st.session_state:
        return False
    return st.session_state['user'].get('role') == 'admin'

def main():
    if not is_admin_user():
        st.error("Доступ запрещен. Требуются права администратора.")
        return
    
    st.title("Административная панель")
    
    tabs = st.tabs([
        "Пользователи",
        "Подписки",
        "Транзакции",
        "Планы",
        "Промокоды"
    ])
    
    with tabs[0]:
        st.header("Управление пользователями")
        
    with tabs[1]:
        st.header("Все подписки")
        
    with tabs[2]:
        st.header("Все транзакции")
        
    with tabs[3]:
        st.header("Управление тарифными планами")
        
    with tabs[4]:
        st.header("Управление промокодами")

if __name__ == "__main__":
    main()