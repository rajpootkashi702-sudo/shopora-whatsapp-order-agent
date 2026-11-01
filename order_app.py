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
    st.caption("Customer ban kar baat karein — bilkul WhatsApp jaisa!")

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
