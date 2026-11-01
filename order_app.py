"""SaleSathi — Mobile App 📱
======================
Multi-business WhatsApp-style order agent.

🔑 Login | 📝 Sign Up (username + password auto-generate)
Har business ka apna: settings, products, orders, agent.

Chalayein:
  streamlit run order_app.py
"""

import pandas as pd
import streamlit as st

from agent import OrderAgent
from config import DEFAULT_SETTINGS
from users import (ensure_seed, create_user, verify, get_settings,
                   save_settings_for, get_orders, add_order)

st.set_page_config(page_title="SaleSathi", page_icon="🤖",
                   layout="centered")

ensure_seed()  # pehli dafa purana admin migrate ho jaye

# ------------------------------------------------------------ mobile CSS
st.markdown("""
<style>
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    h1 { font-size: 1.6rem !important; }
    .stButton > button { width: 100%; padding: 0.75rem 1rem; font-size: 1rem; }
}
.big-cred { font-size: 1.4rem; font-weight: bold; background: #f0f2f6;
            padding: 0.6rem 1rem; border-radius: 0.5rem; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------ auth screen
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.username:
    st.title("🤖 SaleSathi")
    st.caption("Apne business ke liye AI order-taking agent! "
               "Aapka apna sales sathi! 💪")
    tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Sign Up"])

    with tab_login:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("➡️ Login", use_container_width=True):
            if verify(u, p):
                st.session_state.username = u.strip()
                st.session_state.settings = get_settings(u.strip())
                st.session_state.agent = OrderAgent(
                    settings=st.session_state.settings,
                    save_fn=lambda o: add_order(st.session_state.username, o))
                st.session_state.chat = []
                st.rerun()
            else:
                st.error("❌ Ghalat username ya password!")

    with tab_signup:
        st.write("**Naya business account banayein** — username aur password "
                 "khud generate ho jayenge! 🎉")
        shop = st.text_input("🏪 Business / Dukaan ka naam *", key="su_shop")
        owner = st.text_input("👤 Aapka naam", key="su_owner")
        wa = st.text_input("📞 WhatsApp number", key="su_wa")
        if st.button("✨ Account Banayein", use_container_width=True):
            if not shop.strip():
                st.error("❌ Business ka naam to likhein!")
            else:
                username, password = create_user(shop, owner, wa)
                st.session_state.new_cred = (username, password)
                st.rerun()

    # sign-up ke baad credentials bari screen par dikhayein
    if st.session_state.get("new_cred"):
        username, password = st.session_state.new_cred
        st.success("🎉 **Account ban gaya!** Neeche login details **screenshot "
                   "me save kar lein** — password dobara nahi dikhega!")
        st.write("👤 Username:")
        st.markdown('<div class="big-cred">{}</div>'.format(username),
                    unsafe_allow_html=True)
        st.write("🔑 Password:")
        st.markdown('<div class="big-cred">{}</div>'.format(password),
                    unsafe_allow_html=True)
        if st.button("✅ Samajh gaya — Login par jayein",
                     use_container_width=True):
            del st.session_state.new_cred
            st.rerun()

    st.stop()

# ------------------------------------------------------------ logged-in app
username = st.session_state.username
settings = st.session_state.settings

if "agent" not in st.session_state:
    st.session_state.agent = OrderAgent(
        settings=settings,
        save_fn=lambda o: add_order(username, o))
if "chat" not in st.session_state:
    st.session_state.chat = []
if "phone" not in st.session_state:
    st.session_state.phone = "app-customer"

tab_chat, tab_orders, tab_settings = st.tabs(
    ["💬 Customer Chat", "📦 Orders", "⚙️ Settings"])

with tab_chat:
    st.title("🤖 {} Order Agent".format(settings["shop_name"]))
    st.caption("Customer ban kar baat karein — bilkul WhatsApp jaisa! "
               "| 👤 {} | ⚡ by SaleSathi".format(username))
    if st.button("🚪 Logout"):
        for k in ("username", "settings", "agent", "chat"):
            st.session_state.pop(k, None)
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
        st.session_state.agent = OrderAgent(
            settings=st.session_state.settings,
            save_fn=lambda o: add_order(username, o))
        st.rerun()

with tab_orders:
    st.title("📦 Orders")
    orders = get_orders(username)
    if orders:
        df = pd.DataFrame(orders)
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
                           "orders_{}.csv".format(username), "text/csv")
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
            save_settings_for(username, new_settings)
            st.session_state.settings = new_settings
            st.session_state.agent = OrderAgent(
                settings=new_settings,
                save_fn=lambda o: add_order(username, o))
            st.success("✅ Save ho gaya! Agent ab **{}** ke naye settings "
                       "par chal raha hai! 🎉".format(new_settings["shop_name"]))
            st.rerun()

    if b2.button("↩️ Reset (default Shopora)", use_container_width=True):
        save_settings_for(username, DEFAULT_SETTINGS)
        st.session_state.settings = get_settings(username)
        st.session_state.agent = OrderAgent(
            settings=st.session_state.settings,
            save_fn=lambda o: add_order(username, o))
        st.success("✅ Default settings wapas laga di!")
        st.rerun()
