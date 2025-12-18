import streamlit as st
import requests
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000/api"

st.set_page_config(
    page_title="Subscription Management",
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
        st.error(f"Error loading plans: {e}")
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
        st.error(f"Error loading subscriptions: {e}")
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
        st.error(f"Error loading promocodes: {e}")
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
        st.error(f"Error loading transactions: {e}")
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
        st.error(f"Error purchasing subscription: {e}")
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
        st.error(f"Error canceling subscription: {e}")
        return None

def format_date(date_string):
    if not date_string:
        return "Not specified"
    try:
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_string

def format_price(price):
    """Format price"""
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
            <p><strong>Duration:</strong> {plan['duration_days']} days</p>
        </div>
        """, unsafe_allow_html=True)
        
        if on_select:
            if st.button(f"Select {plan['name']}", key=f"select_{plan['id']}"):
                on_select(plan)

def display_subscription_card(subscription):
    status_class = f"status-{subscription['status']}"
    status_text = {
        'active': 'Active',
        'expired': 'Expired',
        'pending': 'Pending payment',
        'canceled': 'Canceled',
        'pending_renewal': 'Pending renewal'
    }.get(subscription['status'], subscription['status'])
    
    with st.container():
        # Форматируем цену для отображения
        plan_price = subscription['plan']['price']
        formatted_price = format_price(plan_price)
        
        st.markdown(f"""
        <div class="subscription-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3>{subscription['plan']['name']}</h3>
                    <p><span class="{status_class}">{status_text}</span></p>
                </div>
                <div style="text-align: right;">
                    <p><strong>Price:</strong> {formatted_price}</p>
                </div>
            </div>
            <div style="margin-top: 1rem;">
                <p><strong>Start:</strong> {format_date(subscription['start_date'])}</p>
                <p><strong>End:</strong> {format_date(subscription['end_date'])}</p>
                <p><strong>Days remaining:</strong> {subscription.get('days_remaining', 0)}</p>
                <p><strong>Auto-renewal:</strong> {'Enabled' if subscription['auto_renew'] else 'Disabled'}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if subscription['status'] == 'active':
                if st.button("Cancel subscription", key=f"cancel_{subscription['id']}"):
                    response = cancel_subscription(subscription['id'])
                    if response and response.status_code == 200:
                        st.success("Subscription canceled")
                        st.rerun()
                    else:
                        st.error("Error canceling subscription")
        with col2:
            if subscription['status'] == 'expired':
                if st.button("Renew", key=f"renew_{subscription['id']}"):
                    st.info("Renewal function will be available in the next update")

def main():
    if st.button("Back to Home", key="back_home"):
        st.switch_page("app.py")
    
    if 'access_token' not in st.session_state:
        st.warning("Please log in")
        if st.button("Go to Authentication", use_container_width=True):
            st.switch_page("pages/01_auth.py")
        return
    
    user = st.session_state.get('user', {})
    
    st.markdown(f"<h1 class='main-header'>Subscription Management</h1>", unsafe_allow_html=True)
    st.markdown(f"**User:** {user.get('username', '')} | **Role:** {user.get('role', '')}")
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "Available Plans",
        "My Subscriptions",
        "Transaction History",
        "Promo Codes"
    ])
    
    with tab1:
        st.header("Available Subscription Plans")
        
        plans = fetch_subscription_plans()
        
        if not plans:
            st.info("No subscription plans available")
        else:
            col1, col2 = st.columns([3, 1])
            with col2:
                sort_by = st.selectbox("Sort by:", ["Price (asc)", "Price (desc)", "Duration"])
            
            # Сортировка с преобразованием цены в число
            if sort_by == "Price (asc)":
                plans = sorted(plans, key=lambda x: float(x['price']) if isinstance(x['price'], str) else x['price'])
            elif sort_by == "Price (desc)":
                plans = sorted(plans, key=lambda x: float(x['price']) if isinstance(x['price'], str) else x['price'], reverse=True)
            
            cols = st.columns(min(3, len(plans)))
            selected_plan = None
            
            for idx, plan in enumerate(plans):
                with cols[idx % len(cols)]:
                    display_plan_card(plan, lambda p: st.session_state.update({'selected_plan': p}))
            
            if 'selected_plan' in st.session_state:
                st.markdown("---")
                selected_plan = st.session_state['selected_plan']
                
                st.subheader(f"Subscribe to: {selected_plan['name']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Description:** {selected_plan['description']}")
                    st.markdown(f"**Price:** {format_price(selected_plan['price'])}")
                    st.markdown(f"**Duration:** {selected_plan['duration_days']} days")
                
                with col2:
                    promocodes = fetch_promocodes()
                    valid_promocodes = [p for p in promocodes if p.get('is_valid', False)]
                    
                    promo_options = ["No promo code"] + [f"{p['code']} (-{p['discount_percent']}%)" for p in valid_promocodes]
                    selected_promo = st.selectbox("Promo code", promo_options)
                    
                    promo_code = ""
                    if selected_promo != "No promo code":
                        promo_code = selected_promo.split(" ")[0]
                        promo = next(p for p in valid_promocodes if p['code'] == promo_code)
                        discount = promo['discount_percent']
                        # Преобразуем цену в число для расчетов
                        price_num = float(selected_plan['price']) if isinstance(selected_plan['price'], str) else selected_plan['price']
                        final_price = price_num * (100 - discount) / 100
                        st.info(f"Price with discount: **{format_price(final_price)}** (-{discount}%)")
                
                if st.button("Subscribe", type="primary", use_container_width=True):
                    with st.spinner("Processing payment..."):
                        response = purchase_subscription(selected_plan['id'], promo_code)
                        
                        if response:
                            if response.status_code == 201:
                                data = response.json()
                                st.success("Subscription successfully created")
                                
                                st.markdown(f"**Subscription ID:** {data.get('subscription_id')}")
                                st.markdown(f"**Transaction ID:** {data.get('transaction_id')}")
                                if data.get('end_date'):
                                    st.markdown(f"**Valid until:** {format_date(data.get('end_date'))}")
                                
                                if 'selected_plan' in st.session_state:
                                    del st.session_state['selected_plan']
                                st.rerun()
                            elif response.status_code == 402:
                                data = response.json()
                                st.error(f"Payment error: {data.get('message', 'Unknown error')}")
                            else:
                                st.error(f"Error: {response.status_code} - {response.text}")
    
    with tab2:
        st.header("My Subscriptions")
        
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Active", "Expired", "Canceled", "Pending payment"]
        )
        
        subscriptions = fetch_my_subscriptions()
        
        if not subscriptions:
            st.info("You have no active subscriptions")
        else:
            filtered_subs = subscriptions
            if status_filter == "Active":
                filtered_subs = [s for s in subscriptions if s['status'] == 'active']
            elif status_filter == "Expired":
                filtered_subs = [s for s in subscriptions if s['status'] == 'expired']
            elif status_filter == "Canceled":
                filtered_subs = [s for s in subscriptions if s['status'] == 'canceled']
            elif status_filter == "Pending payment":
                filtered_subs = [s for s in subscriptions if s['status'] == 'pending']
            
            active_count = len([s for s in subscriptions if s['status'] == 'active'])
            total_count = len(subscriptions)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total subscriptions", total_count)
            col2.metric("Active", active_count)
            if total_count > 0:
                col3.metric("Active %", f"{(active_count/total_count*100):.1f}%")
            
            st.markdown("---")
            
            for subscription in filtered_subs:
                display_subscription_card(subscription)
    
    with tab3:
        st.header("Transaction History")
        
        transactions = fetch_transactions()
        
        if not transactions:
            st.info("No transaction data")
        else:
            table_data = []
            for t in transactions:
                table_data.append({
                    "Date": format_date(t['created_at']),
                    "Type": t['transaction_type'].replace('_', ' ').title(),
                    "Amount": format_price(t['amount']),
                    "Status": t['status'].title(),
                    "Description": t['description']
                })
            
            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn("Date"),
                    "Type": st.column_config.TextColumn("Operation type"),
                    "Amount": st.column_config.TextColumn("Amount"),
                    "Status": st.column_config.TextColumn("Status"),
                    "Description": st.column_config.TextColumn("Description", width="large")
                }
            )
            
            st.markdown("---")
            st.subheader("Statistics")
            
            successful = len([t for t in transactions if t['status'] == 'completed'])
            failed = len([t for t in transactions if t['status'] == 'failed'])
            
            # Суммируем с преобразованием в число
            total_amount = 0
            for t in transactions:
                if t['status'] == 'completed':
                    try:
                        amount = float(t['amount']) if isinstance(t['amount'], str) else t['amount']
                        total_amount += amount
                    except (ValueError, TypeError):
                        pass
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Successful operations", successful)
            col2.metric("Failed", failed)
            col3.metric("Total amount", f"{total_amount:.2f} RUB")
    
    with tab4:
        st.header("Available Promo Codes")
        
        promocodes = fetch_promocodes()
        
        if not promocodes:
            st.info("No promo codes available")
        else:
            show_only_valid = st.checkbox("Show only valid", value=True)
            
            if show_only_valid:
                promocodes = [p for p in promocodes if p.get('is_valid', False)]
            
            cols = st.columns(min(3, len(promocodes)))
            
            for idx, promo in enumerate(promocodes):
                with cols[idx % len(cols)]:
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
                        <h3 style="color: #388E3C;">{promo['code']}</h3>
                        <p><strong>Discount:</strong> {promo['discount_percent']}%</p>
                        <p><small>{promo['description']}</small></p>
                        <p><strong>Used:</strong> {promo['used_count']}/{promo['max_uses']}</p>
                        <p><strong>Valid until:</strong> {format_date(promo['valid_to'])}</p>
                        <p><strong>Status:</strong> {'Valid' if promo.get('is_valid', False) else 'Invalid'}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.info("How to use promo code: Select a promo code when subscribing in the 'Available Plans' tab. The discount will be applied automatically.")
    
    with st.sidebar:
        st.markdown("### Quick Actions")
        
        if st.button("Refresh data", use_container_width=True):
            st.rerun()
        
        if st.button("Logout", use_container_width=True):
            for key in ['access_token', 'refresh_token', 'user']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()