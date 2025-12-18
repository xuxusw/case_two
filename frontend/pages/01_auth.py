import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000/api/auth"

st.set_page_config(
    page_title="Авторизация",
    page_icon=":key:",
    layout="centered"
)

st.markdown("""
<style>
    .auth-container {
        max-width: 600px;
        margin: 0 auto;
        padding: 2rem;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
        font-size: 1rem;
        width: 100%;
        margin-top: 1rem;
    }
    .stButton>button:hover {
        background-color: #388E3C;
    }
    .back-button {
        background-color: #757575;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def login(username, password):
    try:
        response = requests.post(f"{API_BASE_URL}/login/", json={"username": username, "password": password})
        if response.status_code == 200:
            data = response.json()
            st.session_state['access_token'] = data['access']
            st.session_state['refresh_token'] = data['refresh']
            st.session_state['user'] = data['user']
            st.success("Вход успешен.")
            return True
        else:
            st.error("Ошибка входа. Проверьте вводные данные.")
            return False
    except requests.exceptions.ConnectionError:
        st.error("Не удается подключиться к серверу.")
        return False
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def register(username, password, password2, email, first_name, last_name, phone):
    try:
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
            st.success("Регистрация успешна. Теперь Вы можете войти.")
            return True
        else:
            errors = response.json()
            error_msg = "Ошибка регистрации: "
            for key, value in errors.items():
                error_msg += f"{key}: {value} "
            st.error(error_msg)
            return False
    except requests.exceptions.ConnectionError:
        st.error("Не удается подключиться к серверу.")
        return False
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def main():
    if st.button("На главную страницу", key="back_home"):
        st.switch_page("app.py")
    
    st.title("Авторизация")
    st.markdown("---")
    
    if 'access_token' in st.session_state:
        user = st.session_state.get('user', {})
        st.write(f"Вы вошли как: **{user.get('username', '')}**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Перейкти к подпискам", use_container_width=True):
                st.switch_page("pages/02_subscriptions.py")
        with col2:
            if st.button("Выйти", use_container_width=True):
                for key in ['access_token', 'refresh_token', 'user']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        return
    
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])
    
    with tab1:
        st.subheader("Вход")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", type="primary")
            
            if submit:
                if username and password:
                    with st.spinner("Logging in..."):
                        success = login(username, password)
                        if success:
                            st.rerun()
                else:
                    st.warning("Fill all fields")
    
    with tab2:
        st.subheader("Регистрация")
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Username*")
                password = st.text_input("Password*", type="password")
                password2 = st.text_input("Repeat password*", type="password")
                email = st.text_input("Email")
            with col2:
                first_name = st.text_input("First name")
                last_name = st.text_input("Last name")
                phone = st.text_input("Phone")
            
            st.caption("* Required fields")
            submit = st.form_submit_button("Register", type="primary")
            
            if submit:
                if username and password and password2:
                    with st.spinner("Registering..."):
                        success = register(username, password, password2, email, first_name, last_name, phone)
                        if success:
                            st.rerun()
                else:
                    st.warning("Fill required fields")

if __name__ == "__main__":
    main()