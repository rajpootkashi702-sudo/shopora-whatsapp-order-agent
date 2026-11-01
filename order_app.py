"""Shopora Order Agent — Mobile App 📱
====================================
Streamlit app: customer chat (WhatsApp jaisa) + orders dashboard.

Chalayein:
  streamlit run order_app.py
"""

import json
import os

import pandas as pd
import streamlit as st

from agent import OrderAgent, ORDERS_FILE, SHOP_NAME

st.set_page_config(page_title="Shopora Order Agent", page_icon="🤖",
                   layout="centered")

# ------------------------------------------------------------ simple login
# 🔑 APNA LOGIN YAHAN SET KAREIN (username: password)
# NOTE: Ye demo-level lock hai. Repo PUBLIC hai to ye password sab dekh
# sakte hain — asal security ke liye Streamlit Secrets use karein.
APP_USERS = {
    "admin": "shopora2026",
}


def _check_login(username, password):
    return APP_USERS.get(username.strip()) == password


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_user" not in st.session_state:
    st.session_state.login_user = ""

if not st.session_state.logged_in:
    st.title("🔐 Shopora Order Agent")
    st.caption("Login karke andar jayein")
    u = st.text_input("Username", key="login_u")
    p = st.text_input("Password", type="password", key="login_p")
    if st.button("➡️ Login", use_container_width=True):
        if _check_login(u, p):
            st.session_state.logged_in = True
            st.session_state.login_user = u.strip()
            st.rerun()
        else:
            st.error("❌ Ghalat username ya password! Dobara try karein.")
    st.stop()

# ------------------------------------------------------------ mobile CSS

# Mobile-friendly tweaks
st.markdown("""
<style>
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    h1 { font-size: 1.6rem !important; }
    .stButton > button { width: 100%; padding: 0.75rem 1rem; font-size: 1rem; }
}
</style>
""", unsafe_allow_html=True)

if "agent" not in st.session_state:
    st.session_state.agent = OrderAgent()
if "chat" not in st.session_state:
    st.session_state.chat = []
if "phone" not in st.session_state:
    st.session_state.phone = "app-customer"

tab_chat, tab_orders = st.tabs(["💬 Customer Chat", "📦 Orders"])

with tab_chat:
    st.title("🤖 {} Order Agent".format(SHOP_NAME))
    st.caption("Customer ban kar baat karein — bilkul WhatsApp jaisa! "
               "| 👤 {} | ".format(st.session_state.login_user))
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.login_user = ""
        st.session_state.chat = []
        st.rerun()

    for who, text in st.session_state.chat:
        with st.chat_message(who):
            st.write(text)

    prompt = st.chat_input("Message likhein...")
    if prompt:
        st.session_state.chat.append(("user", prompt))
        with st.chat_message("user"):
            st.write(prompt)
        reply = st.session_state.agent.handle_message(
            st.session_state.phone, prompt)
        st.session_state.chat.append(("assistant", reply))
        with st.chat_message("assistant"):
            st.write(reply)

    if st.button("🔄 Nayi chat shuru karein"):
        st.session_state.chat = []
        st.session_state.agent = OrderAgent()
        st.rerun()

with tab_orders:
    st.title("📦 Orders")
    orders = []
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f)
        except (json.JSONDecodeError, OSError):
            orders = []
    if orders:
        df = pd.DataFrame(orders)
        cols = [c for c in ["order_id", "name", "phone", "product",
                            "price_aed", "city", "status", "time"]
                if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        st.metric("Total orders", len(df),
                  "{} AED".format(int(df["price_aed"].sum()))
                  if "price_aed" in df.columns else None)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ CSV Download", csv,
                           "shopora_orders.csv", "text/csv")
    else:
        st.info("Abhi koi order nahi — pehle 💬 chat me order karein!")
