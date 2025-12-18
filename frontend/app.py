import streamlit as st
import requests

st.set_page_config(
    page_title="Subscription System",
    page_icon=":key:",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        background-color: white;
    }
    .app-card:hover {
        border-color: #4CAF50;
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .feature-list {
        text-align: left;
        margin: 2rem 0;
        background-color: #F9F9F9;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #388E3C;
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>Subscription Management System</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-list">
    <h3>For Users:</h3>
    <ul>
    <li>Secure registration and login</li>
    <li>Multiple subscription plans</li>
    <li>Promo codes and discounts</li>
    <li>Payment history</li>
    <li>Subscription management</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-list">
    <h3>Technologies:</h3>
    <ul>
    <li><strong>Backend:</strong> Django REST Framework</li>
    <li><strong>Frontend:</strong> Streamlit</li>
    <li><strong>Authentication:</strong> JWT tokens</li>
    <li><strong>Payments:</strong> Fake gateway (for testing)</li>
    <li><strong>Database:</strong> SQLite</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

st.markdown("### Quick Start")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="app-card">
        <h2>Authentication</h2>
        <p>Login or register new account</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Авторизация", key="auth_btn", use_container_width=True):
        st.switch_page("pages/01_auth.py")

with col2:
    st.markdown("""
    <div class="app-card">
        <h2>Subscription Management</h2>
        <p>View and manage your subscriptions</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Подписки", key="subs_btn", use_container_width=True):
        st.switch_page("pages/02_subscriptions.py")

st.markdown("---")
st.markdown("Поддержка")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Email:**")
    st.markdown("support@subscription-system.com")
with col2:
    st.markdown("**Phone:**")
    st.markdown("+1 (555) 123-4567")
with col3:
    st.markdown("**Working hours:**")
    st.markdown("Mon-Fri: 9:00-18:00")

st.markdown("---")
st.markdown("System Status")

try:
    response = requests.get("http://127.0.0.1:8000/api/subscriptions/plans/", timeout=3)
    if response.status_code == 200:
        st.success("Backend Django is available")
    else:
        st.warning("Backend responds with error")
except:
    st.error("Backend Django is unavailable. Make sure the server is running.")