import streamlit as st

st.set_page_config(
    page_title="Система подписок",
    layout="centered"
)

# Кастомный CSS
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #4CAF50;
        font-size: 3rem;
        margin-bottom: 2rem;
    }
    .app-card {
        border: 2px solid #E0E0E0;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    .app-card:hover {
        border-color: #4CAF50;
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .feature-list {
        text-align: left;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Заголовок
st.markdown("<h1 class='main-title'>Система подписок</h1>", unsafe_allow_html=True)

st.markdown("""
<div class="feature-list">
<h3>Возможности системы:</h3>
<ul>
<li>Безопасная регистрация и авторизация</li>
<li>Множество тарифных планов</li>
<li>Промокоды и скидки</li>
<li>Автопродление подписок</li>
<li>История транзакций</li>
<li>Управление подписками</li>
</ul>
</div>
""", unsafe_allow_html=True)

# Карточки приложений
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="app-card">
        <h2>Авторизация</h2>
        <p>Вход в систему или регистрация нового пользователя</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Перейти к авторизации", key="auth_btn", use_container_width=True):
        st.switch_page("frontend/auth_app.py")

with col2:
    st.markdown("""
    <div class="app-card">
        <h2>Управление подписками</h2>
        <p>Просмотр и управление вашими подписками</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Перейти к подпискам", key="subs_btn", use_container_width=True):
        st.switch_page("frontend/subscription_app.py")

# Информация о системе
st.markdown("---")
st.markdown("###Технологии")
st.markdown("""
- **Бэкенд:** Django + Django REST Framework
- **Фронтенд:** Streamlit
- **Аутентификация:** JWT Tokens
- **База данных:** SQLite (для разработки)
""")

st.markdown("###Поддержка")
st.markdown("""
При возникновении вопросов или проблем обращайтесь:
- Email: support@subscription-system.ru
- Телефон: +7 (999) 123-45-67
""")