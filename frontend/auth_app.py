import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000/api/auth"
BACKGROUND_COLOR = "#FFFFFF"
ACCENT_COLOR = "#4CAF50"
TEXT_COLOR = "#333333"

st.set_page_config(page_title="Авторизация", layout="centered")

# кастомный CSS 
st.markdown(f"""
<style>
    .stApp {{
        background-color: {BACKGROUND_COLOR};
    }}
    .css-1d391kg, .css-12oz5g7 {{
        color: {TEXT_COLOR};
    }}
    .stButton>button {{
        background-color: {ACCENT_COLOR};
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
    }}
    .stButton>button:hover {{
        background-color: #45a049;
    }}
    .stTextInput>div>div>input, .stTextInput>div>div>input:focus {{
        border-color: {ACCENT_COLOR};
    }}
</style>
""", unsafe_allow_html=True)

def login(username, password):
    response = requests.post(f"{API_BASE_URL}/login/", json={"username": username, "password": password})
    if response.status_code == 200:
        data = response.json()
        st.session_state['access_token'] = data['access']
        st.session_state['refresh_token'] = data['refresh']
        st.session_state['user'] = data['user']
        st.success("Вход выполнен успешно")
        return True
    else:
        st.error("Ошибка входа. Проверьте учетные данные.")
        return False

def register(username, password, password2, email, first_name, last_name, phone):
    data = {
        "username": username,
        "password": password,
        "password2": password2,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone
    }
    response = requests.post(f"{API_BASE_URL}/register/", json=data)
    if response.status_code == 201:
        st.success("Регистрация прошла успешно. Теперь вы можете войти.")
        return True
    else:
        errors = response.json()
        error_msg = "Ошибка регистрации: "
        for key, value in errors.items():
            error_msg += f"{key}: {value} "
        st.error(error_msg)
        return False

def main():
    st.title("Система подписок")
    st.markdown("---")

    if 'access_token' in st.session_state:
        st.write(f"Вы вошли как: **{st.session_state['user']['username']}**")
        if st.button("Выйти"):
            for key in ['access_token', 'refresh_token', 'user']:
                if key in st.session_state:
                    del st.session_state[key]
            st.experimental_rerun()
        return

    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    with tab1:
        with st.form("login_form"):
            st.subheader("Вход в систему")
            username = st.text_input("Имя пользователя")
            password = st.text_input("Пароль", type="password")
            submit = st.form_submit_button("Войти")
            if submit:
                if username and password:
                    login(username, password)
                else:
                    st.warning("Заполните все поля")

    with tab2:
        with st.form("register_form"):
            st.subheader("Регистрация")
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Имя пользователя*")
                password = st.text_input("Пароль*", type="password")
                password2 = st.text_input("Повторите пароль*", type="password")
                email = st.text_input("Email")
            with col2:
                first_name = st.text_input("Имя")
                last_name = st.text_input("Фамилия")
                phone = st.text_input("Телефон")
            submit = st.form_submit_button("Зарегистрироваться")
            if submit:
                if username and password and password2:
                    register(username, password, password2, email, first_name, last_name, phone)
                else:
                    st.warning("Обязательные поля отмечены *")

if __name__ == "__main__":
    main()