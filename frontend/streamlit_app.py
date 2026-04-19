import streamlit as st
import requests
import json
import os
import pandas as pd
import plotly.express as px

# Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")

st.set_page_config(
    page_title="RecSys Platform",
    page_icon="🎯",
    layout="wide"
)

# Load CSS
def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css()

# API Helpers
def fetch_users():
    try:
        # Mock users for demo if endpoint not fully implemented
        return [
            {"user_id": "u1001", "username": "Alice", "interactions": 150},
            {"user_id": "u1002", "username": "Bob", "interactions": 42},
            {"user_id": "u1003", "username": "Charlie", "interactions": 89}
        ]
    except Exception:
        return []

def fetch_recommendations(user_id):
    try:
        res = requests.get(f"{API_GATEWAY_URL}/api/v1/recommendations", params={"user_id": user_id}, timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.sidebar.error(f"Failed to fetch recommendations: {e}")
    
    # Mock fallback
    return {
        "user_id": user_id,
        "items": [
            {"item_id": "i2001", "score": 0.95, "rank": 1},
            {"item_id": "i2002", "score": 0.88, "rank": 2},
            {"item_id": "i2003", "score": 0.76, "rank": 3}
        ],
        "experiment_group": "treatment",
        "model_version": "v1.2.0-bpr",
        "served_from_cache": False,
        "response_time_ms": 120
    }

def submit_event(user_id, item_id, event_type, rating=None):
    payload = {
        "user_id": user_id,
        "item_id": item_id,
        "event_type": event_type,
        "timestamp": pd.Timestamp.now().isoformat()
    }
    if event_type == "rating" and rating is not None:
        payload["rating"] = rating
        
    try:
        res = requests.post(f"{API_GATEWAY_URL}/api/v1/events", json=payload, timeout=2)
        if res.status_code in [200, 201]:
            return True
    except Exception:
        pass
    return False

# Sidebar
st.sidebar.title("🎯 RecSys Demo")
st.sidebar.markdown("Select a user to view personalized recommendations.")

users = fetch_users()
user_options = {f"{u['username']} ({u['user_id']})": u['user_id'] for u in users}
selected_user_display = st.sidebar.selectbox("Select User", options=list(user_options.keys()))
selected_user_id = user_options[selected_user_display]

if st.sidebar.button("Refresh Recommendations"):
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown("### System Health")
try:
    health_res = requests.get(f"{API_GATEWAY_URL}/health", timeout=1)
    if health_res.status_code == 200:
        st.sidebar.success("✅ API Gateway: Online")
    else:
        st.sidebar.warning("⚠️ API Gateway: Degraded")
except Exception:
    st.sidebar.error("❌ API Gateway: Offline")

# Main Content
tab1, tab2 = st.tabs(["Recommendations", "A/B Testing Dashboard"])

with tab1:
    st.header(f"Recommendations for {selected_user_display.split(' ')[0]}")
    
    recs_data = fetch_recommendations(selected_user_id)
    
    # Metadata Row
    col1, col2, col3, col4 = st.columns(4)
    exp_color = "green" if recs_data.get("experiment_group") == "treatment" else "blue"
    
    col1.metric("Experiment Group", recs_data.get("experiment_group", "unknown").upper())
    col2.metric("Model Version", recs_data.get("model_version", "unknown"))
    col3.metric("Response Time", f"{recs_data.get('response_time_ms', 0)} ms")
    col4.metric("Cache Status", "HIT" if recs_data.get("served_from_cache") else "MISS")
    
    st.divider()
    
    # Recommendations Grid
    items = recs_data.get("items", [])
    if not items:
        st.info("No recommendations found for this user.")
    else:
        # Layout in rows of 3
        cols = st.columns(3)
        for idx, item in enumerate(items):
            with cols[idx % 3]:
                st.markdown(f"### Item {item['item_id']}")
                st.markdown(f"**Score:** {item['score']:.4f}")
                st.markdown(f"**Rank:** {item['rank']}")
                
                # Interaction buttons
                c1, c2 = st.columns(2)
                if c1.button("👁️ View", key=f"view_{item['item_id']}"):
                    if submit_event(selected_user_id, item['item_id'], "view"):
                        st.toast(f"View event logged for {item['item_id']}!", icon="✅")
                    else:
                        st.toast(f"Failed to log view.", icon="❌")
                        
                if c2.button("👆 Click", key=f"click_{item['item_id']}"):
                    if submit_event(selected_user_id, item['item_id'], "click"):
                        st.toast(f"Click event logged for {item['item_id']}!", icon="✅")
                    else:
                        st.toast(f"Failed to log click.", icon="❌")
                        
                # Rating
                rating = st.slider("Rating", 1.0, 5.0, 3.0, 0.5, key=f"rate_val_{item['item_id']}")
                if st.button("⭐ Submit Rating", key=f"rate_btn_{item['item_id']}"):
                    if submit_event(selected_user_id, item['item_id'], "rating", rating):
                        st.toast(f"Rating {rating} logged for {item['item_id']}!", icon="✅")
                    else:
                        st.toast(f"Failed to log rating.", icon="❌")
                
                st.markdown("---")

with tab2:
    st.header("A/B Testing Metrics")
    st.markdown("Live experiment monitoring.")
    
    # Mock data for demonstration
    exp_data = pd.DataFrame({
        "Group": ["Control (A)", "Treatment (B)"],
        "Users": [15234, 15301],
        "Views": [45100, 48200],
        "Clicks": [1205, 1450],
    })
    exp_data["CTR"] = exp_data["Clicks"] / exp_data["Views"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(exp_data.style.format({"CTR": "{:.2%}"}))
    
    with col2:
        fig = px.bar(exp_data, x="Group", y="CTR", color="Group", title="Click-Through Rate by Group",
                     color_discrete_map={"Control (A)": "blue", "Treatment (B)": "green"})
        st.plotly_chart(fig, use_container_width=True)
