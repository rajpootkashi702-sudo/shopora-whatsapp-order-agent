"""Order Agent — Mobile App 📱
============================
Har business ke liye configurable WhatsApp-style order agent.

Tabs: 💬 Customer Chat (WhatsApp jaisa) + 📦 Orders dashboard + ⚙️ Settings
(Settings me dukaan ka naam, products, prices, WhatsApp number sab badlein!)

Chalayein:
  streamlit run order_app.py
"""

import json
import os

import pandas as pd
import streamlit as st

from agent import OrderAgent, ORDERS_FILE, reload_config
from config import load_settings, save_settings, DEFAULT_SETTINGS

st.set_page_config(page_title="Order Agent", page_icon="🤖",
                   layout="centered")

# Settings sab se pehle (login screen par bhi dukaan ka naam dikhe)
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()
settings = st.session_state.settings

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
    st.title("🔐 {} Order Agent".format(settings["shop_name"]))
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

tab_chat, tab_orders, tab_settings = st.tabs(
    ["💬 Customer Chat", "📦 Orders", "⚙️ Settings"])

with tab_chat:
    st.title("🤖 {} Order Agent".format(settings["shop_name"]))
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
        # purane orders me "price_aed" tha, naye me "price"
        if "price" not in df.columns and "price_aed" in df.columns:
            df["price"] = df["price_aed"]
        cols = [c for c in ["order_id", "name", "phone", "product",
                            "price", "city", "status", "time"]
                if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        st.metric("Total orders", len(df),
                  "{} {}".format(int(df["price"].sum()), settings["currency"])
                  if "price" in df.columns else None)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ CSV Download", csv,
                           "orders.csv", "text/csv")
    else:
        st.info("Abhi koi order nahi — pehle 💬 chat me order karein!")

with tab_settings:
    st.title("⚙️ Business Settings")
    st.caption("Apne business ke hisaab se set karein — **Save** karte hi "
               "agent foran naye settings par chal parega! 🚀")

    s = st.session_state.settings
    shop = st.text_input("🏪 Dukaan / Business ka naam",
                         value=s.get("shop_name", ""))
    c1, c2 = st.columns(2)
    currency = c1.text_input("💱 Currency (jaise: AED, PKR, Rs)",
                             value=s.get("currency", ""))
    order_prefix = c2.text_input("🧾 Order ID prefix (jaise: SHP)",
                                 value=s.get("order_prefix", ""))
    whatsapp = st.text_input("📞 WhatsApp number (orders ke liye)",
                             value=s.get("whatsapp", ""))
    delivery = st.text_area("🚚 Delivery info",
                            value=s.get("delivery_info", ""))

    st.subheader("📦 Products")
    st.caption("Neeche table me **direct edit** karein — naam, price, wazahat. "
               "Nayi row add karne ke liye aakhri khaali row use karein, "
               "hatane ke liye row select karke 🗑️ dabayein.")
    df_prod = pd.DataFrame(s.get("products", []))
    for col in ["name", "price", "desc"]:
        if col not in df_prod.columns:
            df_prod[col] = "" if col != "price" else 0
    edited = st.data_editor(
        df_prod[["name", "price", "desc"]],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "name": st.column_config.TextColumn("Product ka naam",
                                                required=True),
            "price": st.column_config.NumberColumn("Price", min_value=0,
                                                   required=True),
            "desc": st.column_config.TextColumn("Wazahat"),
        },
        key="products_editor",
    )

    b1, b2 = st.columns(2)
    if b1.button("💾 Save Settings", use_container_width=True):
        products = []
        for i, row in enumerate(edited.to_dict("records"), 1):
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            try:
                price = int(float(row.get("price") or 0))
            except (TypeError, ValueError):
                price = 0
            products.append({"id": i, "name": name, "price": price,
                             "desc": str(row.get("desc", "")).strip()})
        if not products:
            st.error("❌ Kam az kam 1 product to rakhein!")
        else:
            new_settings = {
                "shop_name": shop.strip() or "My Shop",
                "currency": currency.strip() or "AED",
                "whatsapp": whatsapp.strip(),
                "delivery_info": delivery.strip(),
                "order_prefix": order_prefix.strip() or "SHP",
                "products": products,
            }
            save_settings(new_settings)
            reload_config()
            st.session_state.settings = new_settings
            st.session_state.agent = OrderAgent()  # taaza settings ke saath
            st.success("✅ Save ho gaya! Agent ab **{}** ke naye settings "
                       "par chal raha hai! 🎉".format(new_settings["shop_name"]))
            st.rerun()

    if b2.button("↩️ Reset (default Shopora)", use_container_width=True):
        save_settings(DEFAULT_SETTINGS)
        reload_config()
        st.session_state.settings = load_settings()
        st.session_state.agent = OrderAgent()
        st.success("✅ Default settings wapas laga di!")
        st.rerun()
